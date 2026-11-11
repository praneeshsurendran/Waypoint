import type { Snapshot, Stop } from '@/types/models'
import type { RouteEventKind } from '@/types/routeHistory'

import { assignedDriverLoad, deliveryDay } from '@/utils/driverWorkflow'

export function recordRouteEvent(
  snapshot: Snapshot,
  kind: RouteEventKind,
  detail: string,
  stop?: Stop,
) {
  const load = assignedDriverLoad(snapshot)
  if (!load) return
  const at = new Date().toISOString()
  ;(snapshot.routeEvents ??= []).push({
    id: crypto.randomUUID(),
    at,
    day: deliveryDay(
      ['loaderConfirmed', 'released'].includes(kind)
        ? at
        : (snapshot.settings.routeStartedAt ?? at),
    ),
    vehicleId: load.vehicleId,
    trip: load.trip,
    revision: snapshot.settings.routeRevision,
    kind,
    detail,
    stopId: stop?.id,
    outletId: stop?.outlet,
  })
}
