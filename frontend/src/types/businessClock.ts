export interface BusinessClock {
  now: Date
  /** Clock time orders close, e.g. "16:00". */
  cutoff: string
  /** True once the clock has passed the cutoff, whether or not intake was closed. */
  cutoffPassed: boolean
  /** True when intake has actually been closed for the delivery day. */
  cutoffClosed: boolean
  minutesToCutoff: number
  /** The day the orders placed now will be delivered. */
  deliveryDate: Date
  /** The first run after `deliveryDate`, used for deferred and drafted orders. */
  nextRunDate: Date
  /** The day an order placed now is delivered: `deliveryDate`, or the following run after the cutoff. */
  orderDate: Date
}
