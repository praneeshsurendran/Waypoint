import type { components as Operations } from '@/types/generated/operations'
import type { components as Identity } from '@/types/generated/identity'

export type ApiDevicePosition = Operations['schemas']['PositionOut']
export type OutletRef = {
  name: string
  lat?: number | undefined
  lng?: number | undefined
  window?: string | undefined
}
export type ApiOrder = Operations['schemas']['OrderOut']
export type ApiStop = Operations['schemas']['StopOut']
export type ApiTrip = Operations['schemas']['TripOut']
export type ApiPlan = Operations['schemas']['PlanOut']
export type ApiAdminUser = Identity['schemas']['AdminUserOut']
export type ApiAuditRow = Operations['schemas']['AuditOut']
