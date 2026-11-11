import { request } from '@/api/client/apiClient'
import type { LoginResponse } from '@/types/api/reference'

export const authApi = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
}

/** Backend auth transport; callers supply their typed response projection. */
export function patchAuthMe<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/auth/me', options)
}
