import { photoDigest } from '@/utils/photoDigest'
import type { RouteEvent } from '@/types/routeHistory'
import type { DeliverySyncEvent } from '@/types/deliverySync'
import { fetchEvidenceBlob } from '@/api/client/assets'
import * as driverApi from '@/api/endpoints/driver'
import * as ordersApi from '@/api/endpoints/orders'
import { ApiError } from '@/api/client/apiErrors'
import type { RouteState } from '@/types/api/delivery'
import type { DeliveryApi } from '@/types/api/delivery'
import { getUser } from '@/infrastructure/storage/authSession'
import type { ApiTrip, ApiStop } from '@/types/api/responses'
import { outletReferences } from '@/infrastructure/adapters/http/reference'
import { mapStop } from '@/mappers/operations'

import { localDb } from '@/infrastructure/storage/httpDatabase'

async function queueEvent(
  stopId: string,
  outcome: DeliverySyncEvent['outcome'],
  note?: string,
  id = crypto.randomUUID(),
  details: Partial<DeliverySyncEvent> = {},
) {
  const createdAt = new Date().toISOString()
  const actorId = getUser()?.id
  const route = actorId === undefined ? undefined : await localDb.httpRoutes.get(actorId)
  const evidence = await localDb.evidence.get(id)
  await localDb.queue.put({
    id,
    actorId,
    evidenceId: id,
    stopId,
    createdAt,
    status: 'pending',
    attempts: 0,
    revision: evidence?.revision ?? route?.route.revision ?? 1,
    kind: outcome === 'FAILED' ? 'attempt' : 'delivery',
    message: note,
    event: {
      ...details,
      client_op_id: id,
      stop_id: Number(stopId),
      outcome,
      note,
      recorded_at: createdAt,
    },
  })
}

async function localRouteView(route: RouteState, actorId: number): Promise<RouteState> {
  const view = structuredClone(route)
  const actions = (await localDb.queue.toArray())
    .filter((action) => action.actorId === actorId && action.status !== 'superseded')
    .sort((left, right) => left.createdAt.localeCompare(right.createdAt))
  for (const action of actions) {
    const stop = view.stops.find((candidate) => candidate.id === action.stopId)
    if (!stop || !action.event) continue
    if (action.event.outcome === 'STARTED') view.started = true
    if (action.event.outcome === 'ARRIVED' && stop.status !== 'Delivered') {
      stop.status = 'Arrived'
      stop.arrivedAt = action.event.recorded_at
    }
    if (action.event.outcome === 'DELIVERED' || action.event.outcome === 'PARTIAL') {
      stop.status = action.status === 'accepted' ? 'Delivered' : 'Proof pending'
      stop.proofId = action.evidenceId
    }
    if (['FAILED', 'REFUSED', 'CLOSED'].includes(action.event.outcome))
      stop.status = 'Cannot deliver'
  }
  return view
}

let syncInFlight: Promise<void> | undefined

export function createHttpDeliveryApi(): DeliveryApi {
  return {
    async getRoute() {
      const user = getUser()
      const empty: RouteState = { started: false, revision: 0, stops: [] }
      if (user?.role !== 'DRIVER') return empty
      const cached = await localDb.httpRoutes.get(user.id)
      if (!navigator.onLine) return localRouteView(cached?.route ?? empty, user.id)
      try {
        const resp = await driverApi.getDriverTripsCurrent<ApiTrip | null>()
        const refs = resp ? await outletReferences() : undefined
        const route: RouteState = resp
          ? {
              started: resp.status === 'IN_TRANSIT' || resp.status === 'COMPLETED',
              revision: resp.plan_id ?? 1,
              stops: (resp.stops ?? []).map((stop) => mapStop(stop, refs)),
            }
          : empty
        await localDb.httpRoutes.put({ actorId: user.id, route })
        return localRouteView(route, user.id)
      } catch (error) {
        if (
          cached &&
          (error instanceof TypeError || (error instanceof ApiError && error.status >= 500))
        ) {
          return localRouteView(cached.route, user.id)
        }
        throw error
      }
    },

    async listStops(filter = {}) {
      // Administrators manage people, not deliveries: there are no stops for them to read.
      if (getUser()?.role === 'ADMIN') return []
      const refs = await outletReferences()
      if (filter.outletId) {
        const stops = await ordersApi.getOutletStops<ApiStop[]>(filter.outletId).catch(() => null)
        if (stops) {
          return stops.map((s) => mapStop(s, refs))
        }
      }
      const resp = await driverApi.getDriverTripsCurrent<ApiTrip>().catch(() => null)
      if (resp?.stops) {
        return resp.stops
          .map((s) => mapStop(s, refs))
          .filter((s) => !filter.outletId || s.outlet === filter.outletId)
      }
      const stops = await ordersApi.getOrdersStops<ApiStop[]>().catch(() => [] as ApiStop[])
      return stops.map((s) => mapStop(s, refs))
    },

    async startRoute() {
      if (navigator.onLine) {
        await driverApi.postDriverTripsStart({ method: 'POST' })
        return
      }
      const user = getUser()
      const cached = user ? await localDb.httpRoutes.get(user.id) : undefined
      const next = cached?.route.stops.find(
        (stop) => stop.status === 'Upcoming' || stop.status === 'Arrived',
      )
      if (!cached || !next)
        throw new Error('Load your assigned route online before starting offline.')
      await queueEvent(next.id, 'STARTED', 'Route started offline')
      await localDb.httpRoutes.put({
        actorId: cached.actorId,
        route: { ...cached.route, started: true },
      })
    },

    async arrive(stopId) {
      await queueEvent(stopId, 'ARRIVED')
      await this.sync(navigator.onLine).catch(() => {})
    },

    async saveProof(stopId, proof) {
      const id = crypto.randomUUID()
      await localDb.evidence.put({
        id,
        kind: 'delivery',
        entityId: stopId,
        photo: proof.photo,
        fileName: proof.photo?.name ?? 'delivery-proof.jpg',
        createdAt: new Date().toISOString(),
        quantity: proof.quantity,
        receiver: proof.receiver,
        signature: proof.signature,
        managerSignOff: proof.managerSignOff,
        receiverException: proof.exception,
        revision: proof.capturedRevision ?? 1,
        accepted: false,
      })
      const partial = proof.managerSignOff?.orders.some((order) => order.received < order.expected)
      await queueEvent(
        stopId,
        partial ? 'PARTIAL' : 'DELIVERED',
        `Delivered ${proof.quantity} cases${proof.exception ? `: ${proof.exception}` : ''}`,
        id,
        { receiver_name: proof.receiver || null },
      )
      await localDb.driverProofDrafts.delete(stopId)
      await this.sync(navigator.onLine).catch(() => {})
    },

    async reportIssue(stopId, issue) {
      await queueEvent(stopId, 'FAILED', issue)
      await this.sync(navigator.onLine).catch(() => {})
    },

    async saveAttemptProof(stopId, photo, issue) {
      const id = crypto.randomUUID()
      await localDb.evidence.put({
        id,
        kind: 'attempt',
        entityId: stopId,
        photo,
        fileName: photo?.name ?? 'attempt-proof.jpg',
        createdAt: new Date().toISOString(),
        receiverException: issue,
        revision: 1,
        accepted: false,
      })
      await queueEvent(stopId, 'FAILED', issue, id)
      await this.sync(navigator.onLine).catch(() => {})
    },

    async retryStop(stopId) {
      await queueEvent(stopId, 'ARRIVED', 'Retry stop')
      await this.sync(navigator.onLine).catch(() => {})
    },

    async confirmManagerHandoff(outletId, stopId, proof) {
      const user = getUser()
      const received = proof.managerSignOff?.orders
      if (user?.role !== 'STORE_MANAGER' || user.outlet_id !== outletId || !received?.length) {
        throw new Error('An assigned store manager and signed order quantities are required.')
      }
      const orders = received.map((order) => {
        const orderId = Number(order.orderId)
        if (
          !Number.isSafeInteger(orderId) ||
          orderId <= 0 ||
          !Number.isInteger(order.received) ||
          order.received < 0 ||
          order.received > order.expected
        ) {
          throw new Error('Review the signed order quantities before confirming receipt.')
        }
        return {
          orderId,
          body: {
            outcome: order.received < order.expected ? ('SHORT' as const) : ('FULL' as const),
            received_qty: order.received,
            affected_qty: order.expected - order.received,
            notes: `${proof.receiver}: ${proof.exception || proof.managerSignOff?.remarks || 'Receipt confirmed'}; signed ${proof.managerSignOff?.signedAt}`,
          },
        }
      })
      const id = crypto.randomUUID()
      const createdAt = new Date().toISOString()
      await localDb.transaction('rw', localDb.evidence, localDb.queue, async () => {
        await localDb.evidence.put({
          id,
          kind: 'delivery',
          entityId: stopId,
          photo: proof.photo,
          fileName: proof.photo.name,
          createdAt,
          quantity: proof.quantity,
          receiver: proof.receiver,
          signature: proof.signature,
          managerSignOff: proof.managerSignOff,
          receiverException: proof.exception,
          revision: proof.capturedRevision ?? 1,
          accepted: false,
        })
        await localDb.queue.put({
          id,
          actorId: user.id,
          evidenceId: id,
          stopId,
          createdAt,
          status: 'pending',
          attempts: 0,
          revision: proof.capturedRevision ?? 1,
          kind: 'delivery',
          receipt: { orders },
        })
      })
      await this.sync(navigator.onLine).catch(() => {})
    },

    async reportDelay(stopId, note, revisedEta, kind) {
      await queueEvent(
        stopId,
        'DELAY',
        `${kind ?? 'delay'}: ${note}${revisedEta ? ` (ETA: ${revisedEta})` : ''}`,
      )
      await this.sync(navigator.onLine).catch(() => {})
    },

    async listRouteHistory() {
      const actorId = getUser()?.id
      if (!navigator.onLine)
        return localDb.httpRouteHistory
          .where('actorId')
          .equals(actorId ?? -1)
          .reverse()
          .sortBy('at')
      const remote = await driverApi.getDriverHistory<RouteEvent[]>()
      await localDb.httpRouteHistory.bulkPut(remote.map((event) => ({ ...event, actorId })))
      return remote
    },

    async reopenProofForSignOff(actionId) {
      const user = getUser()
      const action = await localDb.queue.get(actionId)
      if (
        !user ||
        user.role !== 'DRIVER' ||
        !action ||
        action.actorId !== user.id ||
        action.kind !== 'delivery'
      ) {
        throw new Error('Only the assigned driver can reopen this proof.')
      }
      const evidence = await localDb.evidence.get(action.evidenceId)
      if (
        !evidence ||
        evidence.accepted ||
        action.status === 'accepted' ||
        action.status === 'superseded'
      ) {
        throw new Error('Only an unaccepted proof can be reopened.')
      }
      const draft = {
        stopId: action.stopId,
        photo: evidence.photo,
        fileName: evidence.fileName,
        stage: 'attached' as const,
        quantity: evidence.quantity ?? 0,
        receiver: evidence.receiver ?? '',
        exception: evidence.receiverException ?? '',
        acknowledged: false,
        revision: evidence.revision,
        createdAt: new Date().toISOString(),
        photoDigest: await photoDigest(evidence.photo),
      }
      await localDb.transaction('rw', localDb.queue, localDb.driverProofDrafts, async () => {
        const current = await localDb.queue.get(actionId)
        if (
          !current ||
          current.status === 'accepted' ||
          current.status === 'syncing' ||
          current.status === 'superseded'
        )
          throw new Error('Proof state changed; reload before reopening.')
        await localDb.driverProofDrafts.put(draft)
        await localDb.queue.update(actionId, {
          status: 'superseded',
          message: 'Original retained; renewed manager sign-off required.',
        })
      })
    },

    async getProofDraft(stopId) {
      return localDb.driverProofDrafts.get(stopId)
    },

    async listProofDrafts() {
      return localDb.driverProofDrafts.toArray()
    },

    async saveProofDraft(draft) {
      await localDb.driverProofDrafts.put(draft)
    },

    async deleteProofDraft(stopId) {
      await localDb.driverProofDrafts.delete(stopId)
    },

    async getEvidence(id) {
      const found = await localDb.evidence.get(id)
      if (found) return found
      if (id && (id.startsWith('http') || id.startsWith('/uploads'))) {
        try {
          const url = id.startsWith('http')
            ? id
            : `${(import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')}${id}`
          const blob = await fetchEvidenceBlob(url)
          if (blob) {
            const synthetic = {
              id,
              kind: 'delivery' as const,
              entityId: '',
              photo: blob,
              fileName: id.split('/').pop() || 'proof.jpg',
              createdAt: new Date().toISOString(),
              revision: 1,
              accepted: true,
            }
            await localDb.evidence.put(synthetic).catch(() => {})
            return synthetic
          }
        } catch {
          // ignore
        }
      }
      return undefined
    },

    async listQueue() {
      const rows = await localDb.queue.toArray()
      const actorId = getUser()?.id
      return actorId === undefined ? rows : rows.filter((row) => row.actorId === actorId)
    },

    async sync(isOnline, options) {
      if (syncInFlight) return syncInFlight
      const run = async () => {
        if (!isOnline) return
        const allQueued = await localDb.queue.toArray()
        const eligible = allQueued
          .filter((item) =>
            options?.retryFailed
              ? item.status === 'pending' || item.status === 'retry' || item.status === 'syncing'
              : item.status === 'pending' || item.status === 'syncing',
          )
          .slice(0, 200)
        if (!eligible.length) return

        // Sort by creation time (epoch order)
        eligible.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())

        // Mark items as syncing
        for (const item of eligible) {
          item.status = 'syncing'
          item.attempts += 1
          await localDb.queue.put(item)
        }

        // Store the final payload before sending. A lost acknowledgement must replay exactly it.
        const events: DeliverySyncEvent[] = []
        for (const item of eligible) {
          if (getUser()?.id !== undefined && item.actorId !== getUser()?.id) {
            item.status = 'review'
            item.message = 'This record belongs to another signed-in user. Preserve it for review.'
            await localDb.queue.put(item)
            continue
          }
          if (item.receipt) continue
          const evidence = await localDb.evidence.get(item.evidenceId)
          const event: DeliverySyncEvent = item.event ?? {
            client_op_id: item.id,
            stop_id: Number(item.stopId),
            outcome: item.kind === 'attempt' ? 'FAILED' : evidence ? 'DELIVERED' : 'ARRIVED',
            note:
              item.message ??
              (evidence?.quantity !== undefined
                ? `Delivered ${evidence.quantity} cases`
                : undefined),
            receiver_name: evidence?.receiver || null,
            recorded_at: item.createdAt,
          }
          if (evidence?.photo && !event.pod_photo_path) {
            try {
              const form = new FormData()
              form.append('file', evidence.photo, evidence.fileName || 'delivery-proof.jpg')
              form.append('stop_id', item.stopId)
              const uploaded = await driverApi.postDriverUploads<{ path: string }>({
                method: 'POST',
                body: form,
              })
              event.pod_photo_path = uploaded.path
            } catch (problem) {
              item.status =
                problem instanceof ApiError && [403, 409, 413, 415, 422].includes(problem.status)
                  ? 'review'
                  : 'retry'
              item.message = problem instanceof Error ? problem.message : 'Proof upload failed'
              await localDb.queue.put(item)
              continue
            }
          }
          item.event = event
          await localDb.queue.put(item)
          if (evidence?.signature && !event.pod_signature_path) {
            try {
              const form = new FormData()
              form.append('file', evidence.signature, 'signature.png')
              form.append('stop_id', item.stopId)
              const uploaded = await driverApi.postDriverUploads<{ path: string }>({
                method: 'POST',
                body: form,
              })
              event.pod_signature_path = uploaded.path
              item.event = event
              await localDb.queue.put(item)
            } catch (problem) {
              item.status =
                problem instanceof ApiError && [403, 409, 413, 415, 422].includes(problem.status)
                  ? 'review'
                  : 'retry'
              item.message = problem instanceof Error ? problem.message : 'Signature upload failed'
              await localDb.queue.put(item)
              continue
            }
          }
          events.push(event)
        }
        if (!events.length && !eligible.some((item) => item.receipt)) return
        const sent = new Set(events.map((event) => event.client_op_id))

        // Step 3: Dispatch batch to /driver/sync
        try {
          const results = events.length
            ? await driverApi.postDriverSync<
                Array<{ client_op_id: string; accepted: boolean; message?: string }>
              >({
                method: 'POST',
                body: JSON.stringify({ events }),
              })
            : []

          const resultMap = new Map(results.map((r) => [r.client_op_id, r]))

          for (const item of eligible) {
            if (item.receipt) {
              if (item.actorId !== getUser()?.id) {
                await localDb.queue.update(item.id, {
                  status: 'review',
                  message: 'Sign in as the original receipt author.',
                })
                continue
              }
              for (const order of item.receipt.orders) {
                await ordersApi.confirmOrderReceipt(order.orderId, {
                  method: 'POST',
                  body: JSON.stringify(order.body),
                })
              }
              item.status = 'accepted'
              await localDb.queue.put(item)
              await localDb.evidence.update(item.evidenceId, { accepted: true })
              continue
            }
            if (!sent.has(item.id)) continue
            const res = resultMap.get(item.id)
            if (res?.accepted) {
              item.status = 'accepted'
              await localDb.queue.put(item)
              const ev = await localDb.evidence.get(item.evidenceId)
              if (ev) {
                ev.accepted = true
                await localDb.evidence.put(ev).catch(() => {})
              }
            } else {
              item.status = [
                'stop_conflict',
                'idempotency_conflict',
                'forbidden',
                'sync_sequence_conflict',
              ].includes(res?.message ?? '')
                ? 'review'
                : 'retry'
              item.message = res?.message || 'Server rejected event'
              await localDb.queue.put(item)
            }
          }
        } catch (err: unknown) {
          // Network or server error: set to retry
          for (const item of eligible) {
            if (item.status === 'accepted') continue
            item.status =
              err instanceof ApiError && [403, 409, 422].includes(err.status) ? 'review' : 'retry'
            item.message = err instanceof Error ? err.message : 'Sync request failed'
            await localDb.queue.put(item)
          }
          throw err
        }
      }
      syncInFlight = navigator.locks ? navigator.locks.request('waypoint.driver-sync', run) : run()
      try {
        await syncInFlight
      } finally {
        syncInFlight = undefined
      }
    },

    async reviewQueuedRecord(id) {
      const item = await localDb.queue.get(id)
      if (item) {
        item.status = 'pending'
        await localDb.queue.put(item)
      }
    },
  }
}
