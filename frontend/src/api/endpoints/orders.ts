/** Backend OpenAPI owns these contracts; responses are validated before returning. */
import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse, ApiQuery, ApiOptions as ContractOptions } from '@/types/api/contracts'

export function getOutletStops(
  outletId: string,
  options?: ContractOptions<'/orders/stops', 'get'>,
): Promise<ApiResponse<'/orders/stops', 'get'>> {
  return contractRequest('/orders/stops', 'get', { ...options, query: { outlet_id: outletId } })
}

export function getOrdersStops(
  options?: ContractOptions<'/orders/stops', 'get'>,
): Promise<ApiResponse<'/orders/stops', 'get'>> {
  return contractRequest('/orders/stops', 'get', options ?? {})
}

export function getOrdersIntakeStatus(
  options?: ContractOptions<'/orders/intake-status', 'get'>,
): Promise<ApiResponse<'/orders/intake-status', 'get'>> {
  return contractRequest('/orders/intake-status', 'get', options ?? {})
}

export function getOrders(
  query: ApiQuery<'/orders', 'get'> | URLSearchParams | string,
  options?: ContractOptions<'/orders', 'get'>,
): Promise<ApiResponse<'/orders', 'get'>> {
  return contractRequest('/orders', 'get', { ...options, query })
}

export function postOrdersClose(
  options?: ContractOptions<'/orders/close', 'post'>,
): Promise<ApiResponse<'/orders/close', 'post'>> {
  return contractRequest('/orders/close', 'post', options ?? {})
}

export function postOrders(
  options: ContractOptions<'/orders', 'post'>,
): Promise<ApiResponse<'/orders', 'post'>> {
  return contractRequest('/orders', 'post', options)
}

export function listOrders(
  options?: ContractOptions<'/orders', 'get'>,
): Promise<ApiResponse<'/orders', 'get'>> {
  return contractRequest('/orders', 'get', options ?? {})
}

export function patchOrders(
  id: string | number,
  options: ContractOptions<'/orders/{order_id}', 'patch'>,
): Promise<ApiResponse<'/orders/{order_id}', 'patch'>> {
  return contractRequest('/orders/{order_id}', 'patch', { ...options, params: { order_id: id } })
}

export function confirmOrderReceipt(
  id: string | number,
  options: ContractOptions<'/orders/{order_id}/receipt', 'post'>,
): Promise<ApiResponse<'/orders/{order_id}/receipt', 'post'>> {
  return contractRequest('/orders/{order_id}/receipt', 'post', {
    ...options,
    params: { order_id: id },
  })
}

export function reportOrderIssue(
  id: string | number,
  options: ContractOptions<'/orders/{order_id}/issues', 'post'>,
): Promise<ApiResponse<'/orders/{order_id}/issues', 'post'>> {
  return contractRequest('/orders/{order_id}/issues', 'post', {
    ...options,
    params: { order_id: id },
  })
}

export function cancelOrder(
  id: string | number,
  options?: ContractOptions<'/orders/{order_id}/cancel', 'post'>,
): Promise<ApiResponse<'/orders/{order_id}/cancel', 'post'>> {
  return contractRequest('/orders/{order_id}/cancel', 'post', {
    ...options,
    params: { order_id: id },
  })
}

export function getOrdersWithDateFilter(
  query: ApiQuery<'/orders', 'get'> | URLSearchParams | string,
  options?: ContractOptions<'/orders', 'get'>,
): Promise<ApiResponse<'/orders', 'get'>> {
  return contractRequest('/orders', 'get', { ...options, query })
}
