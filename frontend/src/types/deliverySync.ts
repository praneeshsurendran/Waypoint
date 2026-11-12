/** Persist the exact device payload before sending so retries preserve event identity. */
export interface DeliverySyncEvent {
  client_op_id: string
  stop_id: number
  outcome:
    'STARTED' | 'ARRIVED' | 'DELIVERED' | 'PARTIAL' | 'FAILED' | 'REFUSED' | 'CLOSED' | 'DELAY'
  order_id?: number
  note?: string
  pod_photo_path?: string | null
  pod_signature_path?: string | null
  receiver_name?: string | null
  receiver_pin_ok?: boolean
  recorded_at?: string
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
