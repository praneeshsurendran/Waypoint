import { getToken } from '@/infrastructure/storage/authSession'
import { ApiError } from '@/api/client/apiErrors'

export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export async function request(path: string, options: RequestInit = {}): Promise<unknown> {
  return (await requestWithStatus(path, options)).data
}

export async function requestWithStatus(
  path: string,
  options: RequestInit = {},
): Promise<{ status: number; data: unknown }> {
  const token = getToken()
  const isFormData = options.body instanceof FormData
  const headers = new Headers(options.headers)
  if (!isFormData && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!resp.ok) {
    let payload: unknown
    try {
      payload = await resp.json()
    } catch {
      /* Non-JSON failures retain the HTTP status. */
    }
    const object = (value: unknown): value is Record<string, unknown> =>
      !!value && typeof value === 'object' && !Array.isArray(value)
    const detail = object(payload) ? (payload.error ?? payload.detail) : undefined
    const code = object(detail) && typeof detail.code === 'string' ? detail.code : 'API_ERROR'
    const message =
      typeof detail === 'string'
        ? detail
        : object(detail) && typeof detail.message === 'string'
          ? detail.message
          : `HTTP ${resp.status}`
    const retry = resp.headers.get('Retry-After')
    const seconds =
      retry === null
        ? undefined
        : /^\d+$/.test(retry)
          ? Number(retry)
          : Math.max(0, (Date.parse(retry) - Date.now()) / 1000)
    throw new ApiError(
      resp.status,
      code,
      message,
      seconds !== undefined && Number.isFinite(seconds) ? seconds : undefined,
    )
  }

  if (resp.status === 204) return { status: resp.status, data: undefined }
  try {
    const value: unknown = await resp.json()
    return { status: resp.status, data: value }
  } catch {
    throw new ApiError(502, 'INVALID_JSON', 'The server returned invalid JSON.')
  }
}
