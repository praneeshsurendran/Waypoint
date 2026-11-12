import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { contractRequest } from '@/api/client/contractClient'
import { ApiError } from '@/api/client/apiErrors'
import { retryDelay, retryRead } from '@/queries/polling'

const fetchMock = vi.fn<typeof fetch>()
beforeEach(() => {
  vi.stubGlobal('localStorage', { getItem: () => null })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => {
  vi.unstubAllGlobals()
  vi.clearAllMocks()
})

it.each([{ access_token: 'token', user: { role: 'ADMIN' } }, { access_token: 7, user: {} }, null])(
  'rejects malformed success payloads before exposing typed values',
  async (payload) => {
    fetchMock.mockResolvedValue(Response.json(payload))
    await expect(
      contractRequest('/auth/login', 'post', {
        body: { username: 'driver', password: 'password' },
      }),
    ).rejects.toMatchObject({ status: 502, code: 'INVALID_RESPONSE' })
  },
)

it('checks required request fields at runtime before fetching', async () => {
  await expect(contractRequest('/auth/login', 'post', {})).rejects.toMatchObject({
    status: 422,
    code: 'INVALID_REQUEST',
  })
  expect(fetchMock).not.toHaveBeenCalled()
})

it('rejects an undocumented successful status and a wrong scalar response', async () => {
  fetchMock.mockResolvedValueOnce(Response.json({ ok: true }, { status: 202 }))
  await expect(contractRequest('/driver/check-delivery-windows', 'post')).rejects.toMatchObject({
    code: 'INVALID_RESPONSE',
  })
})

it('preserves omission and explicit null in JSON requests', async () => {
  fetchMock.mockResolvedValueOnce(
    Response.json({
      id: 1,
      username: 'driver',
      full_name: 'Driver',
      role: 'DRIVER',
      is_active: true,
    }),
  )
  await contractRequest('/admin/users/{user_id}', 'patch', {
    params: { user_id: 1 },
    body: { phone: null, outlet_id: undefined },
  })
  expect(fetchMock.mock.calls[0]?.[1]?.body).toBe('{"phone":null}')
})

it('preserves Retry-After and never retries forbidden access', () => {
  expect(retryRead(0, new ApiError(403, 'FORBIDDEN', 'Forbidden'))).toBe(false)
  expect(retryRead(0, new ApiError(429, 'LIMITED', 'Slow down', 30))).toBe(true)
  expect(retryDelay(0, new ApiError(429, 'LIMITED', 'Slow down', 30))).toBeGreaterThanOrEqual(30000)
})
