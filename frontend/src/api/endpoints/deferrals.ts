import { request } from '@/api/client/apiClient'

/** Backend deferrals transport; callers supply their typed response projection. */
export function postDeferrals<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/deferrals', options)
}
