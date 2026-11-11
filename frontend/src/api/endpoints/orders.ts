import { request } from '@/api/client/apiClient'

/** Backend orders transport; callers supply their typed response projection. */
export function getOutletStops<T = unknown>(
  outletId: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/orders/stops?outlet_id=${outletId}`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function getOrdersStops<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/orders/stops', options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function getOrdersIntakeStatus<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/orders/intake-status', options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function getOrders<T = unknown>(
  query: string | number | URLSearchParams,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/orders?${query}`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function postOrdersClose<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/orders/close', options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function postOrders<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/orders', options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function listOrders<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/orders', options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function patchOrders<T = unknown>(id: string | number, options?: RequestInit): Promise<T> {
  return request<T>(`/orders/${id}`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function confirmOrderReceipt<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/orders/${id}/receipt`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function reportOrderIssue<T = unknown>(
  id: string | number,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/orders/${id}/issues`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function cancelOrder<T = unknown>(id: string | number, options?: RequestInit): Promise<T> {
  return request<T>(`/orders/${id}/cancel`, options)
}

/** Backend orders transport; callers supply their typed response projection. */
export function getOrdersWithDateFilter<T = unknown>(
  query: string | number | URLSearchParams,
  options?: RequestInit,
): Promise<T> {
  return request<T>(`/orders${query}`, options)
}
