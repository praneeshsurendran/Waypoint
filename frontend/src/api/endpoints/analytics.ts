import { request } from '@/api/client/apiClient'

/** Backend analytics transport; callers supply their typed response projection. */
export function getAnalyticsDemandForecast<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/analytics/demand-forecast', options)
}
