/** Persist the exact device payload before sending so retries preserve event identity. */
export interface DeliverySyncEvent {
  client_op_id: string
  stop_id: number
  outcome:
    'STARTED' | 'ARRIVED' | 'DELIVERED' | 'PARTIAL' | 'FAILED' | 'REFUSED' | 'CLOSED' | 'DELAY'
  order_id?: number | undefined
  note?: string | undefined
  pod_photo_path?: string | null | undefined
  pod_signature_path?: string | null | undefined
  receiver_name?: string | null | undefined
  receiver_pin_ok?: boolean | undefined
  recorded_at?: string | undefined
}

export interface ReceiptSyncCommand {
  orders: {
    orderId: number
    body: {
      outcome: 'FULL' | 'SHORT'
      received_qty: number
      affected_qty: number
      notes: string
    }
  }[]
}
