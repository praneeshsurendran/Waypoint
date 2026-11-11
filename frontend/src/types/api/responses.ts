export interface ApiDevicePosition {
  vehicle_id: string
  lat: number
  lng: number
  accuracy: number
  recorded_at: string
}

export type OutletRef = { name: string; lat?: number; lng?: number; window?: string }

export interface ApiOrder {
  id: number
  reference?: string
  outlet_id: string
  outlet_name?: string
  brand: string
  temperature_class: string
  total_weight: number
  total_volume: number
  total_cases?: number
  status: string
  priority: boolean
  vehicle_id?: string
  trip?: number
  deferral_reason?: string
  window_open?: string
  window_close?: string
  receipt_status?: string
  deferral_acknowledged_at?: string
  scheduled_at?: string
  departed_at?: string
  receipt_report?: {
    kind: string
    received: number
    affected: number
    description: string
    recorded_at?: string
  }
  delivered_at?: string
  delivery_date?: string
  placed_at?: string
  created_at?: string
  updated_at?: string
}

export interface ApiStop {
  id: number
  outlet_id: string
  sequence?: number
  district?: string
  status: string
  planned_eta?: string
  window_open?: string
  window_close?: string
  lat?: number
  lng?: number
  order_ids?: number[]
  total_cases?: number
  proof_id?: string
}

export interface ApiTrip {
  id: number
  plan_id?: number
  vehicle_id: string
  trip_number: number
  status: string
  planned_depart?: string
  planned_return?: string
  planned_weight?: number
  planned_volume?: number
  planned_distance?: number
  planned_fuel?: number
  stops?: ApiStop[]
  photo_path?: string
}

export interface ApiPlan {
  id: number
  delivery_date: string
  status: string
  trips: ApiTrip[]
  summary_json?: Record<string, unknown>
}

export type ApiAdminUser = {
  id: number
  username: string
  full_name: string
  email: string | null
  phone: string | null
  role: string
  is_active: boolean
  outlet_id: string | null
  vehicle_id: string | null
  depot_id: string | null
  created_at?: string | null
  on_route?: boolean
  trip_number?: number | null
}

export type ApiAuditRow = {
  id: number
  at: string
  action: string
  entity_type: string
  entity_id: string
  actor: string | null
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
}
