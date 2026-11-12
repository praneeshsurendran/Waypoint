/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getReferenceDepots(
  options?: ContractOptions<'/reference/depots', 'get'>,
): Promise<ApiResponse<'/reference/depots', 'get'>> {
  return contractRequest('/reference/depots', 'get', options ?? {})
}

export function getReferenceVehicles(
  options?: ContractOptions<'/reference/vehicles', 'get'>,
): Promise<ApiResponse<'/reference/vehicles', 'get'>> {
  return contractRequest('/reference/vehicles', 'get', options ?? {})
}

export function getReferenceVehicle(
  id: string | number,
  options?: ContractOptions<'/reference/vehicles/{vehicle_id}', 'get'>,
): Promise<ApiResponse<'/reference/vehicles/{vehicle_id}', 'get'>> {
  return contractRequest('/reference/vehicles/{vehicle_id}', 'get', {
    ...options,
    params: { vehicle_id: id },
  })
}

export function getReferenceOutlet(
  id: string | number,
  options?: ContractOptions<'/reference/outlets/{outlet_id}', 'get'>,
): Promise<ApiResponse<'/reference/outlets/{outlet_id}', 'get'>> {
  return contractRequest('/reference/outlets/{outlet_id}', 'get', {
    ...options,
    params: { outlet_id: id },
  })
}

export function getReferenceOutlets(
  options?: ContractOptions<'/reference/outlets', 'get'>,
): Promise<ApiResponse<'/reference/outlets', 'get'>> {
  return contractRequest('/reference/outlets', 'get', options ?? {})
}

export function getReferenceStoreManagers(
  options?: ContractOptions<'/reference/store-managers', 'get'>,
): Promise<ApiResponse<'/reference/store-managers', 'get'>> {
  return contractRequest('/reference/store-managers', 'get', options ?? {})
}
