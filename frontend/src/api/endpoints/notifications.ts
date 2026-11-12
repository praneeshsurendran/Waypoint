import { request } from '@/api/client/apiClient'

import type { ApiNotification } from '@/types/api/notifications'

export const listNotifications = () => request<ApiNotification[]>('/notifications?limit=200')
export const readNotification = (id: string) =>
  request(`/notifications/${encodeURIComponent(id)}/read`, { method: 'POST' })
export const checkDeliveryWindows = () =>
  request('/driver/check-delivery-windows', { method: 'POST' })
export const registerPushSubscription = (subscription: unknown) =>
  request('/notifications/push-subscriptions', {
    method: 'POST',
    body: JSON.stringify(subscription),
  })
