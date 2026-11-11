import { request } from '@/api/client/apiClient'

/** Backend admin transport; callers supply their typed response projection. */
export function postAdminVehicles<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/admin/vehicles', options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function postAdminOutlets<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/admin/outlets', options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function getAdminUsers<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/admin/users', options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function getAuditLog<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/admin/audit?limit=500', options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function patchAdminUsers<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/admin/users/${id}`, options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function postAdminUsers<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/admin/users', options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function resetUserPassword<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/admin/users/${id}/reset-password`, options)
}

/** Backend admin transport; callers supply their typed response projection. */
export function reassignUserTrip<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/admin/users/${id}/reassign-trip`, options)
}
