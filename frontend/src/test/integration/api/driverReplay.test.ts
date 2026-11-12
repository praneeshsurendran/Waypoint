import { required } from '@/test/fixtures/required'
import 'fake-indexeddb/auto'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { createHttpDeliveryApi } from '@/infrastructure/adapters/http/delivery'
import { localDb } from '@/infrastructure/storage/httpDatabase'

const fetchMock = vi.fn<typeof fetch>()
const connection = { onLine: false }
beforeEach(async () => {
  await localDb.queue.clear()
  await localDb.evidence.clear()
  await localDb.driverProofDrafts.clear()
  await localDb.httpRouteHistory.clear()
  await localDb.httpRoutes.clear()
  connection.onLine = false
  vi.stubGlobal('navigator', connection)
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('localStorage', { getItem: () => null })
})
afterEach(() => {
  vi.unstubAllGlobals()
  fetchMock.mockReset()
})

it('replays an offline arrival as ARRIVED and never fabricates a delivery', async () => {
  const api = createHttpDeliveryApi()
  await api.arrive('12')
  const queued = required((await localDb.queue.toArray())[0])
  expect(queued.event?.outcome).toBe('ARRIVED')
  fetchMock.mockImplementation(async (_url, options) => {
    const { events } = JSON.parse(String(options?.body))
    expect(events[0].outcome).toBe('ARRIVED')
    return Response.json(
      events.map((event: { client_op_id: string }) => ({
        client_op_id: event.client_op_id,
        accepted: true,
      })),
    )
  })
  await api.sync(true)
  expect((await localDb.queue.get(queued.id))?.status).toBe('accepted')
})

it.each([false, true])(
  'replays exact proof references after a lost acknowledgement (signature: %s)',
  async (signature) => {
    const api = createHttpDeliveryApi()
    await api.saveProof('12', {
      photo: new File(['photo'], 'proof.jpg', { type: 'image/jpeg' }),
      signature: signature ? new Blob(['signature'], { type: 'image/png' }) : undefined,
      quantity: 10,
      receiver: 'Receiver',
      exception: '',
    })
    const requests: string[] = []
    let uploads = 0
    fetchMock.mockImplementation(async (url, options) => {
      if (String(url).endsWith('/driver/uploads')) {
        uploads += 1
        return Response.json({ path: `/uploads/proof-${uploads}.png` })
      }
      requests.push(String(options?.body))
      if (requests.length === 1) throw new TypeError('Response lost after server commit')
      const { events } = JSON.parse(String(options?.body))
      return Response.json(
        events.map((event: { client_op_id: string }) => ({
          client_op_id: event.client_op_id,
          accepted: true,
          message: 'duplicate',
        })),
      )
    })
    await expect(api.sync(true)).rejects.toThrow('Response lost')
    await api.sync(true, { retryFailed: true })
    expect(uploads).toBe(signature ? 2 : 1)
    if (signature)
      expect(JSON.parse(required(requests[0])).events[0].pod_signature_path).toBe(
        '/uploads/proof-2.png',
      )
    expect(requests[0]).toBe(requests[1])
    expect(required((await localDb.queue.toArray())[0]).status).toBe('accepted')
  },
)

it('recovers a syncing record after a browser crash and preserves delays as nonterminal events', async () => {
  const api = createHttpDeliveryApi()
  await api.reportDelay('12', 'Traffic', '07:30', 'delay')
  const item = required((await localDb.queue.toArray())[0])
  expect(item.event?.outcome).toBe('DELAY')
  await localDb.queue.update(item.id, { status: 'syncing' })
  fetchMock.mockResolvedValue(Response.json([{ client_op_id: item.id, accepted: true }]))
  await api.sync(true)
  expect((await localDb.queue.get(item.id))?.status).toBe('accepted')
})

it('keeps partial handoffs partial and never fabricates PIN verification', async () => {
  const api = createHttpDeliveryApi()
  await api.saveProof('12', {
    photo: new File(['photo'], 'proof.png', { type: 'image/png' }),
    quantity: 5,
    receiver: 'Manager',
    exception: 'Five cases missing',
    managerSignOff: {
      method: 'signature',
      managerName: 'Manager',
      remarks: 'Shortage',
      unloaded: true,
      orders: [{ orderId: '1', expected: 10, received: 5 }],
      strokes: [],
      signedAt: new Date().toISOString(),
      photoDigest: 'digest',
      binding: 'binding',
    },
  })
  const queued = required((await localDb.queue.toArray())[0])
  expect(queued.event?.outcome).toBe('PARTIAL')
  expect(queued.event?.receiver_pin_ok).toBeUndefined()
  expect(queued.event?.note).toContain('Five cases missing')
})

it('restores an unaccepted proof for fresh sign-off while retaining the original evidence', async () => {
  vi.stubGlobal('localStorage', {
    getItem: (key: string) =>
      key === 'waypoint.user'
        ? JSON.stringify({
            id: 7,
            username: 'driver',
            full_name: 'Driver',
            is_active: true,
            role: 'DRIVER',
          })
        : null,
  })
  const api = createHttpDeliveryApi()
  await api.saveProof('12', {
    photo: new File(['photo'], 'proof.png', { type: 'image/png' }),
    quantity: 5,
    receiver: 'Manager',
    exception: '',
  })
  const queued = required((await localDb.queue.toArray())[0])
  await api.reopenProofForSignOff(queued.id)
  expect((await localDb.queue.get(queued.id))?.status).toBe('superseded')
  expect(await localDb.evidence.get(queued.evidenceId)).toBeDefined()
  const draft = await localDb.driverProofDrafts.get('12')
  expect(draft?.acknowledged).toBe(false)
  expect(draft?.signature).toBeUndefined()
  expect(draft?.managerSignOff).toBeUndefined()
})

it('retains the mapped route through an offline restart and queues departure without an arrival', async () => {
  vi.stubGlobal('localStorage', {
    getItem: (key: string) =>
      key === 'waypoint.user'
        ? JSON.stringify({
            id: 7,
            username: 'driver',
            full_name: 'Driver',
            is_active: true,
            role: 'DRIVER',
          })
        : null,
  })
  connection.onLine = true
  fetchMock.mockImplementation(async (url) =>
    String(url).includes('/driver/trips/current')
      ? Response.json({
          id: 1,
          plan_id: 9,
          status: 'LOADED',
          vehicle_id: 'V1',
          trip_number: 1,
          stops: [{ id: 12, trip_id: 1, sequence: 1, outlet_id: 'O1', status: 'PENDING' }],
        })
      : Response.json([]),
  )
  const api = createHttpDeliveryApi()
  const route = await api.getRoute()
  expect(route.revision).toBe(9)
  connection.onLine = false
  fetchMock.mockClear()
  const restarted = createHttpDeliveryApi()
  expect(required((await restarted.getRoute()).stops[0]).id).toBe('12')
  await restarted.startRoute()
  expect(fetchMock).not.toHaveBeenCalled()
  const departure = required((await localDb.queue.toArray())[0])
  expect(departure.event?.outcome).toBe('STARTED')
  const offline = await restarted.getRoute()
  expect(offline.started).toBe(true)
  expect(required(offline.stops[0]).status).toBe('Upcoming')
})

it('confirms a manager handoff through idempotent receipt commands without driver privileges', async () => {
  vi.stubGlobal('localStorage', {
    getItem: (key: string) =>
      key === 'waypoint.user'
        ? JSON.stringify({
            id: 8,
            username: 'manager',
            full_name: 'Manager',
            is_active: true,
            role: 'STORE_MANAGER',
            outlet_id: 'O1',
          })
        : null,
  })
  const api = createHttpDeliveryApi()
  await api.confirmManagerHandoff('O1', '12', {
    photo: new File(['photo'], 'proof.png', { type: 'image/png' }),
    quantity: 5,
    receiver: 'Manager',
    exception: 'Shortage',
    managerSignOff: {
      method: 'signature',
      managerName: 'Manager',
      remarks: '',
      unloaded: true,
      orders: [{ orderId: '21', expected: 10, received: 5 }],
      strokes: [],
      signedAt: '2026-11-12T01:00:00Z',
      photoDigest: 'digest',
      binding: 'binding',
    },
  })
  const payloads: string[] = []
  fetchMock.mockImplementation(async (url, options) => {
    expect(String(url)).toContain('/orders/21/receipt')
    payloads.push(String(options?.body))
    if (payloads.length === 1) throw new TypeError('Receipt acknowledgement lost')
    return Response.json({ ok: true, receipt_status: 'SHORT' }, { status: 201 })
  })
  await expect(api.sync(true)).rejects.toThrow('acknowledgement lost')
  await api.sync(true, { retryFailed: true })
  expect(payloads[0]).toBe(payloads[1])
  expect(JSON.parse(required(payloads[0]))).toMatchObject({
    outcome: 'SHORT',
    received_qty: 5,
    affected_qty: 5,
  })
  expect(required((await localDb.queue.toArray())[0]).status).toBe('accepted')
})

it('does not expose another authenticated actor’s cached private evidence', async () => {
  let actor = 7
  vi.stubGlobal('window', { location: { origin: 'http://localhost:8000' } })
  vi.stubGlobal('localStorage', {
    getItem: (key: string) =>
      key === 'waypoint.user'
        ? JSON.stringify({
            id: actor,
            username: 'user',
            full_name: 'User',
            role: 'DRIVER',
            is_active: true,
          })
        : null,
  })
  const id = '/uploads/private-proof.png'
  await localDb.evidence.put({
    id,
    actorId: 7,
    kind: 'delivery',
    entityId: '12',
    photo: new Blob(['private']),
    fileName: 'private.png',
    createdAt: new Date().toISOString(),
    revision: 1,
    accepted: true,
  })
  const api = createHttpDeliveryApi()
  expect((await api.getEvidence(id))?.actorId).toBe(7)
  expect(fetchMock).not.toHaveBeenCalled()
  actor = 8
  fetchMock.mockResolvedValueOnce(new Response(null, { status: 403 }))
  expect(await api.getEvidence(id)).toBeUndefined()
  expect(fetchMock).toHaveBeenCalledOnce()
  // Preserve the original owner's local proof rather than deleting it on account changes.
  actor = 7
  expect((await api.getEvidence(id))?.actorId).toBe(7)
})
