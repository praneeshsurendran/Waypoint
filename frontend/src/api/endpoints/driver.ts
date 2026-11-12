/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getDriverTripsCurrent(
  options?: ContractOptions<'/driver/trips/current', 'get'>,
): Promise<ApiResponse<'/driver/trips/current', 'get'>> {
  return contractRequest('/driver/trips/current', 'get', options ?? {})
}

export function postDriverTripsStart(
  options?: ContractOptions<'/driver/trips/start', 'post'>,
): Promise<ApiResponse<'/driver/trips/start', 'post'>> {
  return contractRequest('/driver/trips/start', 'post', options ?? {})
}

export function recordStopEvent(
  id: string | number,
  options: ContractOptions<'/driver/stops/{stop_id}/events', 'post'>,
): Promise<ApiResponse<'/driver/stops/{stop_id}/events', 'post'>> {
  return contractRequest('/driver/stops/{stop_id}/events', 'post', {
    ...options,
    params: { stop_id: id },
  })
}

export function postDriverUploads(
  options: ContractOptions<'/driver/uploads', 'post'>,
): Promise<ApiResponse<'/driver/uploads', 'post'>> {
  return contractRequest('/driver/uploads', 'post', options)
}

export function postDriverSync(
  options: ContractOptions<'/driver/sync', 'post'>,
): Promise<ApiResponse<'/driver/sync', 'post'>> {
  return contractRequest('/driver/sync', 'post', options)
}

export function postDriverPositions(
  options: ContractOptions<'/driver/positions', 'post'>,
): Promise<ApiResponse<'/driver/positions', 'post'>> {
  return contractRequest('/driver/positions', 'post', options)
}

export function getDriverPositionsLatest(
  options?: ContractOptions<'/driver/positions/latest', 'get'>,
): Promise<ApiResponse<'/driver/positions/latest', 'get'>> {
  return contractRequest('/driver/positions/latest', 'get', options ?? {})
}

export function getDriverHistory(
  options?: ContractOptions<'/driver/history', 'get'>,
): Promise<ApiResponse<'/driver/history', 'get'>> {
  return contractRequest('/driver/history', 'get', options ?? {})
}
