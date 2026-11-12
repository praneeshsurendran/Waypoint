/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiQuery, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getLoadingTrips(
  options?: ContractOptions<'/loading/trips', 'get'>,
): Promise<ApiResponse<'/loading/trips', 'get'>> {
  return contractRequest('/loading/trips', 'get', options ?? {})
}

export function getLoadingTripsWithDepotFilter(
  query: ApiQuery<'/loading/trips', 'get'> | URLSearchParams | string,
  options?: ContractOptions<'/loading/trips', 'get'>,
): Promise<ApiResponse<'/loading/trips', 'get'>> {
  return contractRequest('/loading/trips', 'get', { ...options, query })
}

export function getLoadingTrip(
  id: string | number,
  options?: ContractOptions<'/loading/trips/{trip_id}', 'get'>,
): Promise<ApiResponse<'/loading/trips/{trip_id}', 'get'>> {
  return contractRequest('/loading/trips/{trip_id}', 'get', { ...options, params: { trip_id: id } })
}

export function reportLoadingFlag(
  id: string | number,
  options: ContractOptions<'/loading/trips/{trip_id}/flags', 'post'>,
): Promise<ApiResponse<'/loading/trips/{trip_id}/flags', 'post'>> {
  return contractRequest('/loading/trips/{trip_id}/flags', 'post', {
    ...options,
    params: { trip_id: id },
  })
}

export function releaseLoadingTrip(
  id: string | number,
  options?: ContractOptions<'/loading/trips/{trip_id}/release', 'post'>,
): Promise<ApiResponse<'/loading/trips/{trip_id}/release', 'post'>> {
  return contractRequest('/loading/trips/{trip_id}/release', 'post', {
    ...options,
    params: { trip_id: id },
  })
}
