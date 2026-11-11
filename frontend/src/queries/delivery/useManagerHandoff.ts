import { useApiQuery } from '@/queries/useApiQuery'
import type { Session } from '@/types/session'

export function useManagerHandoff(session: Pick<Session, 'outletId'>, stopId: string) {
  return useApiQuery(['manager-handoff', session.outletId, stopId], async (apis) => {
    const [stops, orders, draft, route, settings] = await Promise.all([
      apis.delivery.listStops({ outletId: session.outletId }),
      apis.orders.listOrders({ outletId: session.outletId }),
      apis.delivery.getProofDraft(stopId),
      apis.delivery.getRoute(),
      apis.account.getSettings(),
    ])
    return {
      stop: stops.find(
        (stop) =>
          stop.id === stopId &&
          stop.outlet === session.outletId &&
          (route.stops.length === 0 || route.stops.some((assigned) => assigned.id === stop.id)),
      ),
      orders,
      draft,
      started: route.started || route.stops.length === 0,
      settings,
    }
  })
}
