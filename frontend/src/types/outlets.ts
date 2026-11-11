/**
 * What the system knows about an outlet when its manager places an order: the brand (which sets the
 * ordering schedule) and when goods may be received. A backend serves these from `outlets.csv`
 * (brand, `parking_constraint`, `mall_window`); the demo models three.
 */
export interface ReceivingLimits {
  /** Earliest a delivery may start and latest it may finish, "HH:MM". */
  earliest: string
  latest: string
  /** Shortest window worth offering, in minutes, and the step between choices. */
  shortest: number
  step: number
  /** Why the limits exist, shown under the picker. */
  reason: string
}

export type Brand = 'Fresh' | 'Style' | 'Tech'

export type Parking = 'normal' | 'van_only' | 'mall_dock'

export interface OutletProfile {
  id: string
  name: string
  brand: Brand
  district: string
  depot: string
  receiving: ReceivingLimits
  /** `outlets.csv` `parking_constraint`: any vehicle, vans only, or the mall's delivery window. */
  parking?: Parking
  /** True for mall outlets, which accept deliveries only in the mall's fixed access window. */
  mall: boolean
  /** How often this brand orders: Style weekly for a scheduled day, Tech as needed. */
  schedule: string
  /**
   * The outlet's own delivery window ("HH:MM"), fixed in the outlet data (a mall's access window for
   * mall outlets). Orders do not carry a window of their own. Unset where the source has none.
   */
  window?: { start: string; end: string }
}

/** What an administrator enters to add an outlet; the system assigns the id. */
export interface NewOutlet {
  name: string
  brand: Brand
  district: string
  depot: string
  parking: Parking
  /** The window deliveries may arrive in, "HH:MM". For a mall this is the mall's access window. */
  earliest: string
  latest: string
}
