import { fetchEvidenceBlob } from '@/api/client/assets'
import * as driverApi from '@/api/endpoints/driver'
import * as ordersApi from '@/api/endpoints/orders'
import type { DeliveryApi } from '@/types/api/delivery'
import { getUser } from '@/infrastructure/storage/authSession'
import type { ApiTrip, ApiStop } from '@/types/api/responses'
import { outletReferences } from '@/infrastructure/adapters/http/reference'
import { mapStop } from '@/mappers/operations'

import { localDb } from '@/infrastructure/storage/httpDatabase'

export function createHttpDeliveryApi(): DeliveryApi {
  return {
    async getRoute() {
      // Only the driver has a current route; other roles are refused if they ask for it.
      const driver = getUser()?.role === 'DRIVER'
      const resp = driver
        ? await driverApi.getDriverTripsCurrent<ApiTrip>().catch(() => null)
        : null
      const refs = await outletReferences()
      if (!resp) {
        return {
          started: false,
          revision: 0,
          stops: [],
        }
      }
      return {
        started: resp.status === 'IN_TRANSIT' || resp.status === 'COMPLETED',
        revision: 1,
        stops: (resp.stops ?? []).map((s) => mapStop(s, refs)),
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
      await driverApi.postDriverTripsStart({ method: 'POST' }).catch(() => {})
    },

    async arrive(stopId) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      try {
        await driverApi.recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'ARRIVED',
          }),
        })
      } catch {
        // Offline fallback: queue arrival event for later sync
        await localDb.queue.put({
          id: opId,
          evidenceId: opId,
          stopId,
          createdAt: new Date().toISOString(),
          status: 'pending',
          attempts: 0,
          revision: 1,
          kind: 'delivery',
        })
      }
    },

    async saveProof(stopId, proof) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      let photoUrl = ''

      // 1. Always store full evidence locally in IndexedDB first
      await localDb.evidence
        .put({
          id: opId,
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
        .catch(() => {})

      await localDb.driverProofDrafts.delete(stopId).catch(() => {})

      // 2. Try online upload if connected
      let onlineSuccess: boolean
      try {
        if (proof.photo) {
          const form = new FormData()
          form.append('file', proof.photo)
          form.append('stop_id', stopId)
          const uploadResp = await driverApi
            .postDriverUploads<{ path: string }>({
              method: 'POST',
              body: form,
            })
            .catch(() => null)
          if (uploadResp?.path) {
            const serverOrigin = (
              import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
            ).replace(/\/api\/v1\/?$/, '')
            photoUrl = `${serverOrigin}${uploadResp.path}`
          }
        }

        await driverApi.recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'DELIVERED',
            note: `Delivered ${proof.quantity} cases`,
            pod_photo_path: photoUrl || null,
            receiver_name: proof.receiver || null,
            receiver_pin_ok: true,
          }),
        })

        // Online sync succeeded; mark evidence accepted
        const ev = await localDb.evidence.get(opId)
        if (ev) {
          ev.accepted = true
          await localDb.evidence.put(ev).catch(() => {})
        }
        onlineSuccess = true
      } catch {
        onlineSuccess = false
      }

      // 3. If offline or request failed, queue action for background sync
      if (!onlineSuccess) {
        await localDb.queue.put({
          id: opId,
          evidenceId: opId,
          stopId,
          createdAt: new Date().toISOString(),
          status: 'pending',
          attempts: 0,
          revision: proof.capturedRevision ?? 1,
          kind: 'delivery',
        })
      }
    },

    async reportIssue(stopId, issue) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      try {
        await driverApi.recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'FAILED',
            note: issue,
          }),
        })
      } catch {
        await localDb.queue.put({
          id: opId,
          evidenceId: opId,
          stopId,
          createdAt: new Date().toISOString(),
          status: 'pending',
          attempts: 0,
          revision: 1,
          kind: 'attempt',
          message: issue,
        })
      }
    },

    async saveAttemptProof(stopId, photo, issue) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      let photoUrl = ''
      if (photo) {
        await localDb.evidence
          .put({
            id: opId,
            kind: 'attempt',
            entityId: stopId,
            photo,
            fileName: photo?.name ?? 'attempt-proof.jpg',
            createdAt: new Date().toISOString(),
            receiverException: issue,
            revision: 1,
            accepted: false,
          })
          .catch(() => {})
      }

      try {
        if (photo) {
          const form = new FormData()
          form.append('file', photo)
          form.append('stop_id', stopId)
          const uploadResp = await driverApi
            .postDriverUploads<{ path: string }>({
              method: 'POST',
              body: form,
            })
            .catch(() => null)
          if (uploadResp?.path) {
            const serverOrigin = (
              import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'
            ).replace(/\/api\/v1\/?$/, '')
            photoUrl = `${serverOrigin}${uploadResp.path}`
          }
        }

        await driverApi.recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'FAILED',
            note: photoUrl ? `${issue} | Proof: ${photoUrl}` : issue,
          }),
        })

        const ev = await localDb.evidence.get(opId)
        if (ev) {
          ev.accepted = true
          await localDb.evidence.put(ev).catch(() => {})
        }
      } catch {
        await localDb.queue.put({
          id: opId,
          evidenceId: opId,
          stopId,
          createdAt: new Date().toISOString(),
          status: 'pending',
          attempts: 0,
          revision: 1,
          kind: 'attempt',
          message: issue,
        })
      }
    },

    async retryStop(stopId) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      try {
        await driverApi.recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'ARRIVED',
            note: 'Retry stop',
          }),
        })
      } catch {
        await localDb.queue.put({
          id: opId,
          evidenceId: opId,
          stopId,
          createdAt: new Date().toISOString(),
          status: 'pending',
          attempts: 0,
          revision: 1,
          kind: 'delivery',
        })
      }
    },

    async confirmManagerHandoff(_outletId, stopId, proof) {
      await this.saveProof(stopId, proof)
    },

    async reportDelay(stopId, note, revisedEta, kind) {
      const opId = `op_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`
      await driverApi
        .recordStopEvent(stopId, {
          method: 'POST',
          body: JSON.stringify({
            client_op_id: opId,
            stop_id: Number(stopId),
            outcome: 'PARTIAL',
            note: `${kind ?? 'delay'}: ${note}${revisedEta ? ` (ETA: ${revisedEta})` : ''}`,
          }),
        })
        .catch(() => {})
    },

    async listRouteHistory() {
      return []
    },

    async reopenProofForSignOff() {},

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
      return localDb.queue.toArray()
    },

    async sync(isOnline, options) {
      if (!isOnline) return
      const allQueued = await localDb.queue.toArray()
      const eligible = allQueued.filter((item) =>
        options?.retryFailed
          ? item.status === 'pending' || item.status === 'retry'
          : item.status === 'pending',
      )
      if (!eligible.length) return

      // Sort by creation time (epoch order)
      eligible.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())

      // Mark items as syncing
      for (const item of eligible) {
        item.status = 'syncing'
        item.attempts += 1
        await localDb.queue.put(item)
      }

      // Step 1: Upload any pending photos first
      const serverOrigin = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(
        /\/api\/v1\/?$/,
        '',
      )

      const photoPaths: Record<string, string> = {}
      for (const item of eligible) {
        const ev = await localDb.evidence.get(item.evidenceId)
        if (ev?.photo && !photoPaths[item.id]) {
          try {
            const form = new FormData()
            form.append('file', ev.photo, ev.fileName || 'delivery-proof.jpg')
            form.append('stop_id', item.stopId)
            const uploadResp = await driverApi.postDriverUploads<{ path: string }>({
              method: 'POST',
              body: form,
            })
            if (uploadResp?.path) {
              photoPaths[item.id] = `${serverOrigin}${uploadResp.path}`
            }
          } catch {
            // Upload failure will be caught or retried
          }
        }
      }

      // Step 2: Build sync batch events
      const events = []
      for (const item of eligible) {
        const ev = await localDb.evidence.get(item.evidenceId)
        if (item.kind === 'delivery') {
          events.push({
            client_op_id: item.id,
            stop_id: Number(item.stopId),
            outcome: 'DELIVERED',
            note: ev?.quantity !== undefined ? `Delivered ${ev.quantity} cases` : 'Delivered',
            pod_photo_path: photoPaths[item.id] || null,
            receiver_name: ev?.receiver || null,
            receiver_pin_ok: true,
            recorded_at: item.createdAt,
          })
        } else {
          events.push({
            client_op_id: item.id,
            stop_id: Number(item.stopId),
            outcome: 'FAILED',
            note: photoPaths[item.id]
              ? `${item.message || 'Delivery attempt failed'} | Proof: ${photoPaths[item.id]}`
              : item.message || 'Delivery attempt failed',
            pod_photo_path: photoPaths[item.id] || null,
            recorded_at: item.createdAt,
          })
        }
      }

      // Step 3: Dispatch batch to /driver/sync
      try {
        const results = await driverApi.postDriverSync<
          Array<{ client_op_id: string; accepted: boolean; message?: string }>
        >({
          method: 'POST',
          body: JSON.stringify({ events }),
        })

        const resultMap = new Map(results.map((r) => [r.client_op_id, r]))

        for (const item of eligible) {
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
            item.status = 'retry'
            item.message = res?.message || 'Server rejected event'
            await localDb.queue.put(item)
          }
        }
      } catch (err: unknown) {
        // Network or server error: set to retry
        for (const item of eligible) {
          item.status = 'retry'
          item.message = err instanceof Error ? err.message : 'Sync request failed'
          await localDb.queue.put(item)
        }
        throw err
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
