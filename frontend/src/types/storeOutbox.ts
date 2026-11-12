import type { ReceiptIssue } from '@/types/api/orders'
import type { Order, StoreOrderInput } from '@/types/models'

export type OutboxRequest =
  | { kind: 'orders'; inputs: StoreOrderInput[] }
  | { kind: 'receipt'; orderId: string }
  | { kind: 'issue'; orderId: string; issue: ReceiptIssue }
  | { kind: 'acknowledge'; orderId: string }
  | { kind: 'cancel'; orderId: string }
  | { kind: 'profile'; memberId: string; name: string; mobile: string; email: string }

/** waiting: not sent yet · sending · failed: needs the person · draft: arrived after the cutoff. */
export type OutboxStatus = 'waiting' | 'sending' | 'failed' | 'draft'
export interface OutboxItem {
  id: string
  outletId: string
  request: OutboxRequest
  /** What the person did, in their words: "Confirm 2 Fresh orders". */
  title: string
  createdAt: string
  status: OutboxStatus
  message?: string | undefined
}

/** An order as the store screens see it: possibly changed by something not sent yet. */
export type StoreOrder = Order & { pendingSync?: boolean | undefined }

export type Delivery = { status: 'sent' } | { status: 'draft'; message: string }
