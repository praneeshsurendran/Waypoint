import { useApiQuery } from '@/queries/useApiQuery'
import type { Session } from '@/types/session'
import type { Stop } from '@/types/models'

export function useDeliveryAlerts(session: Pick<Session, 'outletId'>) {
  return useApiQuery(['delivery-alerts', session.outletId], (api) =>
    session.outletId ? api.driverSignals.listNotices(session.outletId) : Promise.resolve([]),
  )
}

export function usePendingHandoffs(session: Pick<Session, 'outletId'>) {
  return useApiQuery(['manager-handoffs', session.outletId], async (apis) => {
    if (!session.outletId) return []
    const [stops, drafts, route] = await Promise.all([
      apis.delivery.listStops({ outletId: session.outletId }),
      apis.delivery.listProofDrafts(),
      apis.delivery.getRoute(),
    ])
    return stops
      .filter(
        (stop) =>
          stop.outlet === session.outletId &&
          stop.status === 'Arrived' &&
          (route.stops.length === 0 ||
            (route.started && route.stops.some((assigned) => assigned.id === stop.id))),
      )
      .map((stop) => ({ stop, draft: drafts.find((draft) => draft.stopId === stop.id) }))
  })
}

export function useStoreContact(stop: Stop) {
  return useApiQuery(['store-contact', stop.outlet], async (apis) => {
    const [members, notices] = await Promise.all([
      apis.team.listMembers(),
      apis.driverSignals.listNotices(stop.outlet),
    ])
    return {
      manager: members.find(
        (member) =>
          member.role === 'store-manager' &&
          member.status === 'Active' &&
          member.outletId === stop.outlet,
      ),
      notices: notices.filter((notice) => notice.stopId === stop.id),
    }
  })
}

export function useProofDrafts() {
  return useApiQuery(['driver', 'drafts'], (apis) => apis.delivery.listProofDrafts())
}
