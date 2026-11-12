/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getAnalyticsDemandForecast(
  options?: ContractOptions<'/analytics/demand-forecast', 'get'>,
): Promise<ApiResponse<'/analytics/demand-forecast', 'get'>> {
  return contractRequest('/analytics/demand-forecast', 'get', options ?? {})
}
