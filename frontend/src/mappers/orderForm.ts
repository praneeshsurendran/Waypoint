import type { Temperature, Order } from '@/types/models'
import { estimateLoad } from '@/utils/orderSizing'

import type { FieldValues } from '@/types/store-manager/orderForm'
import { windowText } from '@/utils/store-manager/orderView'

export const defaultWindow: Record<Temperature, string> = {
  Chilled: '05:30–07:30',
  Ambient: '06:00–08:00',
}

export const round = (value: number, places: number) => String(Number(value.toFixed(places)))

export function loadFor(cases: number) {
  if (!(cases > 0)) return { weight: '', volume: '' }
  const load = estimateLoad('Fresh', cases)
  return { weight: round(load.weight, 1), volume: round(load.volume, 3) }
}

export function valuesFromOrder(temperature: Temperature, order?: Order): FieldValues {
  return order
    ? {
        cases: String(order.cases),
        ...loadFor(order.cases),
        window: windowText(order),
      }
    : { cases: '', weight: '', volume: '', window: defaultWindow[temperature] }
}
