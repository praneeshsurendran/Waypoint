import { request } from '@/api/client/apiClient'

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceDepots<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/reference/depots', options)
}

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceVehicles<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/reference/vehicles', options)
}

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceVehicle<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/reference/vehicles/${id}`, options)
}

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceOutlet<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/reference/outlets/${id}`, options)
}

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceOutlets<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/reference/outlets', options)
}

/** Backend reference transport; callers supply their typed response projection. */
export function getReferenceStoreManagers<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/reference/store-managers', options)
}
