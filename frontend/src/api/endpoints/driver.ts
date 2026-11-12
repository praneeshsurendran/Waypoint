import { request } from '@/api/client/apiClient'

/** Backend driver transport; callers supply their typed response projection. */
export function getDriverTripsCurrent<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/trips/current', options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function postDriverTripsStart<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/trips/start', options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function recordStopEvent<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/driver/stops/${id}/events`, options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function postDriverUploads<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/uploads', options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function postDriverSync<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/sync', options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function postDriverPositions<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/positions', options)
}

/** Backend driver transport; callers supply their typed response projection. */
export function getDriverPositionsLatest<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/positions/latest', options)
}

export function getDriverHistory<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/driver/history', options)
}
