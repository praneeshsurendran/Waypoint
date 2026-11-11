import { useApiQuery } from '@/queries/useApiQuery'
import type { Order } from '@/types/models'

export function useVehicleDetails(order: Pick<Order, 'vehicleId'>) {
  return useApiQuery(['vehicle', order.vehicleId ?? 'none'], async (apis) =>
    order.vehicleId ? ((await apis.fleet.getVehicle(order.vehicleId)) ?? null) : null,
  )
}

export function useDepots() {
  return useApiQuery(['depots'], (apis) => apis.fleet.listDepots())
}
