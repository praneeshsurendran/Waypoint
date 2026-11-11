import { request } from '@/api/client/apiClient'

/** Backend loading transport; callers supply their typed response projection. */
export function getLoadingTrips<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/loading/trips', options)
}

/** Backend loading transport; callers supply their typed response projection. */
export function getLoadingTripsWithDepotFilter<T = unknown>(
  query: string | number | URLSearchParams,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/loading/trips${query}`, options)
}

/** Backend loading transport; callers supply their typed response projection. */
export function getLoadingTrip<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/loading/trips/${id}`, options)
}

/** Backend loading transport; callers supply their typed response projection. */
export function reportLoadingFlag<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/loading/trips/${id}/flags`, options)
}

/** Backend loading transport; callers supply their typed response projection. */
export function releaseLoadingTrip<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/loading/trips/${id}/release`, options)
}
