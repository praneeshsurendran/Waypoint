import { createStubAccountApi } from '@/infrastructure/adapters/http/account'
import { createHttpAnalyticsApi } from '@/infrastructure/adapters/http/analytics'
import { createHttpDeliveryApi } from '@/infrastructure/adapters/http/delivery'
import { createHttpDriverSignalsApi } from '@/infrastructure/adapters/http/driverSignals'
import { createHttpFleetApi } from '@/infrastructure/adapters/http/fleet'
import { createHttpLoadingApi } from '@/infrastructure/adapters/http/loading'
import { createHttpOrdersApi } from '@/infrastructure/adapters/http/orders'
import { createHttpOutletsApi } from '@/infrastructure/adapters/http/outlets'
import { createHttpPlanningApi } from '@/infrastructure/adapters/http/planning'
import { createHttpTeamApi } from '@/infrastructure/adapters/http/team'
import type { Apis } from '@/types/api'

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
