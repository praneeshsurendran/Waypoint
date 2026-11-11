import type { Order } from '@/types/models'
import type { OutboxItem, StoreOrder } from '@/types/storeOutbox'

const isWaiting = (item: OutboxItem) => item.status === 'waiting' || item.status === 'sending'

/** The orders as they will be once the waiting changes are sent. */
export function applyOutbox(orders: Order[], outbox: OutboxItem[]): StoreOrder[] {
  let result: StoreOrder[] = orders
  const change = (orderId: string, patch: Partial<StoreOrder>) => {
    result = result.map((order) =>
      order.id === orderId ? { ...order, ...patch, pendingSync: true } : order,
    )
  }
  for (const item of outbox.filter(isWaiting)) {
    const { request } = item
    if (request.kind === 'orders') {
      // Tech orders stand alone (a new one is added unless an existing order is changed).
      const tech = result[0]?.brand === 'Tech'
      for (const input of request.inputs) {
        const existing = input.orderId
          ? result.find((order) => order.id === input.orderId)
          : tech
            ? undefined
            : result.find((order) => order.temperature === input.temperature)
        // `orderId` only says which order is being changed; it is not an order field.
        const fields = { ...input, orderId: undefined }
        const placed: StoreOrder = {
          ...(existing ?? {
            id: tech
              ? `PENDING-${item.id}`
              : `PENDING-${input.temperature === 'Chilled' ? 'C' : 'A'}`,
            outlet: item.outletId,
            outletName: result[0]?.outletName ?? item.outletId,
            brand: result[0]?.brand ?? 'Fresh',
            priority: false,
            receipt: 'Pending',
          }),
          ...fields,
          status: 'Confirmed',
          vehicleId: undefined,
          trip: undefined,
          placedAt: item.createdAt,
          pendingSync: true,
        }
        result = existing
          ? result.map((order) => (order === existing ? placed : order))
          : [...result, placed]
      }
    } else if (request.kind === 'profile') {
      // Contact details are not part of an order; the page shows what is waiting.
    } else if (request.kind === 'cancel') {
      result = result.filter((order) => order.id !== request.orderId)
    } else if (request.kind === 'receipt') {
      change(request.orderId, { receipt: 'Confirmed', receiptAt: item.createdAt })
    } else if (request.kind === 'issue') {
      change(request.orderId, {
        receipt: 'Issue reported',
        receiptAt: item.createdAt,
        issue: `${request.issue.kind} goods: ${request.issue.description}`,
        receiptReport: { ...request.issue, recordedAt: item.createdAt },
      })
    } else {
      change(request.orderId, {
        deferralAcknowledged: true,
        deferralAcknowledgedAt: item.createdAt,
      })
    }
  }
  return result
}
