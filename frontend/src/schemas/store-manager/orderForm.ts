import type { FieldValues, FormErrors } from '@/types/store-manager/orderForm'
import type { Temperature, StoreOrderInput } from '@/types/models'

import { temperatures } from '@/utils/store-manager/orderView'
import { unitSizes, estimateLoad } from '@/utils/orderSizing'
import { windowProblem, parseWindow } from '@/schemas/store-manager/windows'

export function parseForm(
  values: Record<Temperature, FieldValues>,
  included: Record<Temperature, boolean>,
  /** The outlet's fixed window: when given, orders use it and no window is chosen or checked. */
  fixedWindow?: { start: string; end: string },
) {
  const errors: FormErrors = {}
  const inputs: StoreOrderInput[] = []
  for (const temperature of temperatures) {
    if (!included[temperature]) continue
    const value = values[temperature]
    const problems: Partial<Record<keyof FieldValues, string>> = {}
    const cases = Number(value.cases)
    if (!Number.isInteger(cases) || cases < 1 || cases > unitSizes.Fresh.max)
      problems.cases = `Enter 1 to ${unitSizes.Fresh.max} cases.`
    const windowError = fixedWindow ? undefined : windowProblem(value.window)
    if (windowError) problems.window = windowError
    errors[temperature] = problems
    const window = fixedWindow ?? parseWindow(value.window)
    if (!Object.keys(problems).length && window)
      inputs.push({
        temperature,
        cases,
        ...estimateLoad('Fresh', cases),
        window: window.start,
        windowEnd: window.end,
      })
  }
  const chosen = temperatures.filter((temperature) => included[temperature]).length
  return { valid: chosen > 0 && inputs.length === chosen, inputs, errors, chosen }
}
