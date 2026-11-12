/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getDraftPlans(
  options?: ContractOptions<'/plans', 'get'>,
): Promise<ApiResponse<'/plans', 'get'>> {
  return contractRequest('/plans', 'get', { ...options, query: 'status=DRAFT' })
}

export function getPublishedPlans(
  options?: ContractOptions<'/plans', 'get'>,
): Promise<ApiResponse<'/plans', 'get'>> {
  return contractRequest('/plans', 'get', { ...options, query: 'status=PUBLISHED' })
}

export function postPlansAutoPlan(
  options?: ContractOptions<'/plans/auto-plan', 'post'>,
): Promise<ApiResponse<'/plans/auto-plan', 'post'>> {
  return contractRequest('/plans/auto-plan', 'post', options ?? {})
}

export function patchPlans(
  id: string | number,
  options: ContractOptions<'/plans/{plan_id}', 'patch'>,
): Promise<ApiResponse<'/plans/{plan_id}', 'patch'>> {
  return contractRequest('/plans/{plan_id}', 'patch', { ...options, params: { plan_id: id } })
}

export function validatePlan(
  id: string | number,
  options?: ContractOptions<'/plans/{plan_id}/validate', 'post'>,
): Promise<ApiResponse<'/plans/{plan_id}/validate', 'post'>> {
  return contractRequest('/plans/{plan_id}/validate', 'post', {
    ...options,
    params: { plan_id: id },
  })
}

export function publishPlan(
  id: string | number,
  options?: ContractOptions<'/plans/{plan_id}/publish', 'post'>,
): Promise<ApiResponse<'/plans/{plan_id}/publish', 'post'>> {
  return contractRequest('/plans/{plan_id}/publish', 'post', {
    ...options,
    params: { plan_id: id },
  })
}
