import type { AnalyticsApi } from '@/types/api/analytics'
import type { DriverSignalsApi } from '@/types/api/driverSignals'
import type { AccountApi } from '@/types/api/account'
import type { DeliveryApi } from '@/types/api/delivery'
import type { FleetApi } from '@/types/api/fleet'
import type { LoadingApi } from '@/types/api/loading'
import type { OrdersApi } from '@/types/api/orders'
import type { OutletsApi } from '@/types/api/outlets'
import type { PlanningApi } from '@/types/api/planning'
import type { TeamApi } from '@/types/api/team'

export type * from '@/types/api/analytics'
export type * from '@/types/api/driverSignals'
export type * from '@/types/api/account'
export type * from '@/types/api/delivery'
export type * from '@/types/api/fleet'
export type * from '@/types/api/loading'
export type * from '@/types/api/orders'
export type * from '@/types/api/outlets'
export type * from '@/types/api/planning'
export type * from '@/types/api/team'

/**
 * Everything the screens read and write, grouped by data rather than by role because one
 * order passes through every role. A backend replaces the implementations, not this contract.
 */
export interface Apis {
  driverSignals: DriverSignalsApi
  orders: OrdersApi
  outlets: OutletsApi
  planning: PlanningApi
  loading: LoadingApi
  delivery: DeliveryApi
  fleet: FleetApi
  team: TeamApi
  account: AccountApi
  analytics: AnalyticsApi
}
