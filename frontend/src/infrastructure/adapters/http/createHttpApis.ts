import type { Apis } from '@/types/api'
import { createHttpDriverSignalsApi } from '@/infrastructure/adapters/http/driverSignals'
import { createHttpOrdersApi } from '@/infrastructure/adapters/http/orders'
import { createHttpPlanningApi } from '@/infrastructure/adapters/http/planning'
import { createHttpLoadingApi } from '@/infrastructure/adapters/http/loading'
import { createHttpDeliveryApi } from '@/infrastructure/adapters/http/delivery'
import { createHttpFleetApi } from '@/infrastructure/adapters/http/fleet'
import { createHttpAnalyticsApi } from '@/infrastructure/adapters/http/analytics'
import { createHttpTeamApi } from '@/infrastructure/adapters/http/team'
import { createHttpOutletsApi } from '@/infrastructure/adapters/http/outlets'
import { createStubAccountApi } from '@/infrastructure/adapters/http/account'

export function createHttpApis(outletId?: string): Apis {
  return {
    driverSignals: createHttpDriverSignalsApi(),
    orders: createHttpOrdersApi(outletId),
    planning: createHttpPlanningApi(),
    loading: createHttpLoadingApi(),
    delivery: createHttpDeliveryApi(),
    fleet: createHttpFleetApi(),
    analytics: createHttpAnalyticsApi(),
    team: createHttpTeamApi(),
    outlets: createHttpOutletsApi(),
    account: createStubAccountApi(),
  }
}
