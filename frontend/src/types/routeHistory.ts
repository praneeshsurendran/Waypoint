export type RouteEventKind =
  | 'loaderConfirmed'
  | 'released'
  | 'started'
  | 'arrived'
  | 'proofSaved'
  | 'accepted'
  | 'delay'
  | 'breakdown'
  | 'attempt'
  | 'reopened'
  | 'completed'

export interface RouteEvent {
  id: string
  at: string
  day: string
  vehicleId: string
  trip: number
  revision: number
  kind: RouteEventKind
  detail: string
  stopId?: string
  outletId?: string
}
