/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function postDeferrals(
  options: ContractOptions<'/deferrals', 'post'>,
): Promise<ApiResponse<'/deferrals', 'post'>> {
  return contractRequest('/deferrals', 'post', options)
}
