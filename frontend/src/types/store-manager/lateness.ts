/**
 * A late delivery matters to a store: receiving staff may have moved on, and a Fresh outlet may miss
 * morning sales (booklet, "arrival after the window closes"). These helpers compare the vehicle's
 * expected arrival with the order's receiving window. A backend can supply the expected arrival and a
 * lateness probability; the screens only need the stop's `eta`.
 */
export interface Lateness {
  minutesLate: number
  expected: string
  windowEnd: string
}
