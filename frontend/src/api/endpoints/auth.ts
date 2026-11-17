/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function patchAuthMe(
  options: ContractOptions<'/auth/me', 'patch'>,
): Promise<ApiResponse<'/auth/me', 'patch'>> {
  return contractRequest('/auth/me', 'patch', options)
}

export const authApi = {
  login(username: string, password: string): Promise<ApiResponse<'/auth/login', 'post'>> {
    return contractRequest('/auth/login', 'post', { body: { username, password } })
  },
}

export function requestAccountChange(options: ContractOptions<'/auth/account-change-requests', 'post'>): Promise<ApiResponse<'/auth/account-change-requests', 'post'>> {
  return contractRequest('/auth/account-change-requests', 'post', options)
}
