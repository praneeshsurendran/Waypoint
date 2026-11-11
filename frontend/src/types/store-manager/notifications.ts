export type FeedKind = 'order' | 'delivery' | 'deferral' | 'receipt' | 'issue'

export interface FeedEvent {
  id: string
  at: string
  orderId: string
  kind: FeedKind
  title: string
  detail: string
  /** True while the store still has to do something about it. */
  needsAction?: boolean
}
