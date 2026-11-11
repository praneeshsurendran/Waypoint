import type { OrderForm, FieldValues } from '@/types/store-manager/orderForm'
import type { Temperature, Order } from '@/types/models'

import { useSyncExternalStore } from 'react'
import { subscribe, getSnapshot, write, empty } from '@/infrastructure/storage/orderFormDraft'
import { temperatures } from '@/utils/store-manager/orderView'
import { valuesFromOrder, loadFor } from '@/mappers/orderForm'

import { unitSizes } from '@/utils/orderSizing'

export function useOrderForm(orders: Order[]): OrderForm {
  const current = useSyncExternalStore(subscribe, getSnapshot)
  const saved = (temperature: Temperature) =>
    orders.find((order) => order.temperature === temperature)
  const values = Object.fromEntries(
    temperatures.map((temperature) => [
      temperature,
      current.values[temperature] ?? valuesFromOrder(temperature, saved(temperature)),
    ]),
  ) as Record<Temperature, FieldValues>
  const included = Object.fromEntries(
    temperatures.map((temperature) => [temperature, !current.skipped[temperature]]),
  ) as Record<Temperature, boolean>
  const update = (temperature: Temperature, next: FieldValues) =>
    write({ ...getSnapshot(), values: { ...getSnapshot().values, [temperature]: next } })
  const setCases = (temperature: Temperature, text: string) => {
    const cases = Number(text)
    // Weight and volume always follow the number of cases.
    update(temperature, {
      ...values[temperature],
      cases: text,
      ...loadFor(Number.isFinite(cases) ? cases : 0),
    })
  }
  return {
    values,
    included,
    dirty:
      temperatures.some((temperature) => Boolean(current.values[temperature])) ||
      temperatures.some((temperature) => current.skipped[temperature]),
    change: (temperature, _field, value) => setCases(temperature, value),
    stepCases: (temperature, by) => {
      const next = Math.min(
        unitSizes.Fresh.max,
        Math.max(1, (Number(values[temperature].cases) || 0) + by),
      )
      setCases(temperature, String(next))
    },
    setWindow: (temperature, window) => update(temperature, { ...values[temperature], window }),
    setIncluded: (temperature, include) =>
      write({ ...getSnapshot(), skipped: { ...getSnapshot().skipped, [temperature]: !include } }),
    fillFrom: (previous) =>
      write({
        values: Object.fromEntries(
          temperatures.flatMap((temperature) => {
            const match = previous.find((order) => order.temperature === temperature)
            return match ? [[temperature, valuesFromOrder(temperature, match)]] : []
          }),
        ),
        skipped: Object.fromEntries(
          temperatures.map((temperature) => [
            temperature,
            !previous.some((order) => order.temperature === temperature),
          ]),
        ),
      }),
    reset: () => write(empty()),
  }
}
