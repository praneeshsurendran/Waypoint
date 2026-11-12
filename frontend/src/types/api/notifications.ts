export interface ApiNotification {
  id: string
  type: string
  data: { outlet_id?: string; stop_id?: number; decision?: { reason_code?: string }; note?: string }
  created_at: string
  read: boolean
}
