import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { request } from '@/api/client/apiClient'
import { ApiError } from '@/api/client/apiErrors'
import { getToken, getUser, setToken } from '@/infrastructure/storage/authSession'
import { login, logout } from '@/infrastructure/auth'
import { confirmOrderReceipt } from '@/api/endpoints/orders'
import { publishPlan } from '@/api/endpoints/plans'
import { recordStopEvent } from '@/api/endpoints/driver'

const fetchMock = vi.fn<typeof fetch>()
let values: Map<string, string>

beforeEach(() => {
  values = new Map()
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  })
  vi.stubGlobal('window', { dispatchEvent: vi.fn() })
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

describe('central HTTP transport and endpoint contracts', () => {
  it('forwards authentication, custom headers, credentials, and cancellation', async () => {
    setToken('signed-in-token')
    fetchMock.mockResolvedValueOnce(Response.json({ ok: true }))
    const signal = new AbortController().signal
    await expect(
      request('/probe', { headers: { 'X-Request': 'probe' }, credentials: 'include', signal }),
    ).resolves.toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/probe'),
      expect.objectContaining({
        credentials: 'include',
        signal,
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer signed-in-token',
          'X-Request': 'probe',
        },
      }),
    )
  })

  it('lets the browser set multipart boundaries and accepts empty responses', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))
    const body = new FormData()
    body.append('file', new Blob(['photo'], { type: 'image/png' }), 'proof.png')
    await expect(request('/driver/uploads', { method: 'POST', body })).resolves.toBeUndefined()
    expect(fetchMock.mock.calls[0][1]?.headers).not.toHaveProperty('Content-Type')
  })

  it.each([
    [{ detail: { code: 'LOCKED', message: 'Plan is locked' } }, 'LOCKED', 'Plan is locked'],
    [{ error: { code: 'DENIED', message: 'Access denied' } }, 'DENIED', 'Access denied'],
    [{ detail: 'Invalid quantity' }, 'API_ERROR', 'Invalid quantity'],
  ])('preserves structured backend errors: %j', async (body, code, message) => {
    fetchMock.mockResolvedValueOnce(Response.json(body, { status: 409 }))
    await expect(request('/probe')).rejects.toMatchObject({
      name: 'ApiError',
      status: 409,
      code,
      message,
    })
  })

  it('handles non-JSON errors and forwards cancellation errors', async () => {
    fetchMock.mockResolvedValueOnce(new Response('Unavailable', { status: 503 }))
    await expect(request('/probe')).rejects.toEqual(new ApiError(503, 'API_ERROR', 'HTTP 503'))
    const abort = new DOMException('Cancelled', 'AbortError')
    fetchMock.mockRejectedValueOnce(abort)
    await expect(request('/probe')).rejects.toBe(abort)
  })

  it('keeps receipt, publication, and driver paths and payloads unchanged', async () => {
    fetchMock.mockImplementation(async () => new Response(null, { status: 204 }))
    const body = JSON.stringify({ outcome: 'FULL' })
    await confirmOrderReceipt('42', { method: 'POST', body })
    await publishPlan(7, { method: 'POST' })
    await recordStopEvent('12', { method: 'POST', body: JSON.stringify({ outcome: 'DELIVERED' }) })
    expect(fetchMock.mock.calls.map(([url]) => String(url).replace(/^.*\/api\/v1/, ''))).toEqual([
      '/orders/42/receipt',
      '/plans/7/publish',
      '/driver/stops/12/events',
    ])
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'POST', body })
  })

  it('preserves login payloads, session storage, and logout cleanup', async () => {
    const user = {
      id: 1,
      username: 'driver',
      full_name: 'Driver One',
      role: 'DRIVER',
      is_active: true,
      outlet_id: null,
      vehicle_id: 'VEH055',
      depot_id: 'DEP01',
    }
    fetchMock.mockResolvedValueOnce(
      Response.json({ access_token: 'token', token_type: 'bearer', user }),
    )
    await login('driver', 'password')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ username: 'driver', password: 'password' }),
    })
    expect(getToken()).toBe('token')
    expect(getUser()).toEqual(user)
    values.set('waypoint.lastRole', 'driver')
    logout()
    expect(getToken()).toBeNull()
    expect(getUser()).toBeNull()
    expect(values.has('waypoint.lastRole')).toBe(false)
  })
})

it('authorizes private evidence only at the configured API origin', async () => {
  const { fetchEvidenceBlob } = await import('@/api/client/assets')
  const { BASE_URL } = await import('@/api/client/apiClient')
  vi.stubGlobal('window', { location: { origin: 'http://frontend.example' } })
  values.set('waypoint.token', 'private-token')
  fetchMock.mockResolvedValueOnce(new Response(new Blob(['proof'])))
  await fetchEvidenceBlob(`${new URL(BASE_URL).origin}/uploads/proof.jpg`)
  expect(fetchMock.mock.calls[0][1]?.headers).toEqual({ Authorization: 'Bearer private-token' })
})

it('never forwards the bearer token to an external evidence URL', async () => {
  const { fetchEvidenceBlob } = await import('@/api/client/assets')
  vi.stubGlobal('window', { location: { origin: 'http://frontend.example' } })
  values.set('waypoint.token', 'private-token')
  fetchMock.mockResolvedValueOnce(new Response(new Blob(['proof'])))
  await fetchEvidenceBlob('https://private-objects.example/proof?signature=temporary')
  expect(fetchMock.mock.calls[0][1]?.headers).toBeUndefined()
})
