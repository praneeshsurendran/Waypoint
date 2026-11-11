import { getToken } from '@/infrastructure/storage/authSession'
import { ApiError } from '@/api/client/apiErrors'

export const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const isFormData = options.body instanceof FormData
  const headers: Record<string, string> = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const resp = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!resp.ok) {
    type Problem = { code?: string; message?: string }
    let errorBody: { error?: Problem; detail?: Problem | string } = {}
    try {
      errorBody = await resp.json()
    } catch {
      /* Preserve operation when storage or the error payload is unavailable. */
    }
    // The API reports problems as { detail: { code, message } }; plain strings come from validation.
    const detail =
      typeof errorBody.detail === 'string' ? { message: errorBody.detail } : errorBody.detail
    const problem = errorBody.error ?? detail
    throw new ApiError(
      resp.status,
      problem?.code ?? 'API_ERROR',
      problem?.message ?? `HTTP ${resp.status}`,
    )
  }
  if (resp.status === 204) return undefined as T
  return resp.json() as Promise<T>
}
