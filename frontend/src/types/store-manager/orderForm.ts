import type { Temperature, Order } from '@/types/models'

export interface FieldValues {
  cases: string
  /** Worked out from the cases (see `estimateLoad`); shown to the person but never typed. */
  weight: string
  volume: string
  window: string
}

export type FormErrors = Partial<Record<Temperature, Partial<Record<keyof FieldValues, string>>>>

export interface OrderForm {
  values: Record<Temperature, FieldValues>
  /** Whether each order is part of this submission. */
  included: Record<Temperature, boolean>
  /** True once the person has changed something since the last confirmation. */
  dirty: boolean
  change: (temperature: Temperature, field: 'cases', value: string) => void
  stepCases: (temperature: Temperature, by: number) => void
  setWindow: (temperature: Temperature, window: string) => void
  setIncluded: (temperature: Temperature, included: boolean) => void
  /** Fills the form from an earlier day's orders; a temperature that day had none of is left out. */
  fillFrom: (previous: Order[]) => void
  reset: () => void
}

export interface Edits {
  values: Partial<Record<Temperature, FieldValues>>
  /** Orders the person chose not to place this time (chilled is not ordered every day). */
  skipped: Partial<Record<Temperature, boolean>>
}
