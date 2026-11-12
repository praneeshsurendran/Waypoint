/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function postAdminVehicles(
  options: ContractOptions<'/admin/vehicles', 'post'>,
): Promise<ApiResponse<'/admin/vehicles', 'post'>> {
  return contractRequest('/admin/vehicles', 'post', options)
}

export function postAdminOutlets(
  options: ContractOptions<'/admin/outlets', 'post'>,
): Promise<ApiResponse<'/admin/outlets', 'post'>> {
  return contractRequest('/admin/outlets', 'post', options)
}

export function getAdminUsers(
  options?: ContractOptions<'/admin/users', 'get'>,
): Promise<ApiResponse<'/admin/users', 'get'>> {
  return contractRequest('/admin/users', 'get', options ?? {})
}

export function getAuditLog(
  options?: ContractOptions<'/admin/audit', 'get'>,
): Promise<ApiResponse<'/admin/audit', 'get'>> {
  return contractRequest('/admin/audit', 'get', { ...options, query: 'limit=500' })
}

export function patchAdminUsers(
  id: string | number,
  options: ContractOptions<'/admin/users/{user_id}', 'patch'>,
): Promise<ApiResponse<'/admin/users/{user_id}', 'patch'>> {
  return contractRequest('/admin/users/{user_id}', 'patch', { ...options, params: { user_id: id } })
}

export function postAdminUsers(
  options: ContractOptions<'/admin/users', 'post'>,
): Promise<ApiResponse<'/admin/users', 'post'>> {
  return contractRequest('/admin/users', 'post', options)
}

export function resetUserPassword(
  id: string | number,
  options: ContractOptions<'/admin/users/{user_id}/reset-password', 'post'>,
): Promise<ApiResponse<'/admin/users/{user_id}/reset-password', 'post'>> {
  return contractRequest('/admin/users/{user_id}/reset-password', 'post', {
    ...options,
    params: { user_id: id },
  })
}

export function reassignUserTrip(
  id: string | number,
  options: ContractOptions<'/admin/users/{user_id}/reassign-trip', 'post'>,
): Promise<ApiResponse<'/admin/users/{user_id}/reassign-trip', 'post'>> {
  return contractRequest('/admin/users/{user_id}/reassign-trip', 'post', {
    ...options,
    params: { user_id: id },
  })
}
