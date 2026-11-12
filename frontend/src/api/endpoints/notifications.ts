import { contractRequest } from '@/api/client/contractClient'
import type { ApiResponse } from '@/types/api/contracts'
import type { WebPushRegistration } from '@/types/driverSignals'

export const listNotifications = (): Promise<ApiResponse<'/notifications', 'get'>> =>
  contractRequest('/notifications', 'get', { query: { limit: 200 } })
export const readNotification = (
  id: string,
): Promise<ApiResponse<'/notifications/{event_id}/read', 'post'>> =>
  contractRequest('/notifications/{event_id}/read', 'post', { params: { event_id: id } })
export const checkDeliveryWindows = (): Promise<
  ApiResponse<'/driver/check-delivery-windows', 'post'>
> => contractRequest('/driver/check-delivery-windows', 'post', {})
export const registerPushSubscription = (_subscription: WebPushRegistration): Promise<never> => {
  void _subscription
  return contractRequest('/notifications/push-subscriptions', 'post', {})
}
