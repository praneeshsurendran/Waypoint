import { useApiQuery } from '@/queries/useApiQuery'

export function useDemandForecast() {
  return useApiQuery(['analytics', 'demand-forecast'], (apis) => apis.analytics.demandForecast())
}

export function useOrderQueue(deliveryDay: string) {
  return useApiQuery(['orders', 'queue', deliveryDay], (api) =>
    api.orders.listOrders({ date: deliveryDay }),
  )
}
