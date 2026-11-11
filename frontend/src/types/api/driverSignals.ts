import type { DevicePosition, DeliveryNotice, WebPushRegistration } from '@/types/driverSignals'

/** Replace the local adapter with authenticated HTTP/realtime transport. */
export interface DriverSignalsApi {
  registerPushSubscription(subscription: WebPushRegistration): Promise<void>
  recordPosition(position: DevicePosition): Promise<void>
  pendingPositions(): Promise<DevicePosition[]>
  listNotices(outletId?: string): Promise<DeliveryNotice[]>
  acknowledgeNotice(id: string): Promise<void>
  checkDeliveryWindows(now: string): Promise<void>
}
