export interface ApiUserProfile {
  id: number
  username: string
  full_name: string
  role: string
  is_active: boolean
  outlet_id: string | null
  vehicle_id: string | null
  depot_id: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: ApiUserProfile
}

export interface ApiOutlet {
  outlet_id: string
  name?: string | null
  brand: string
  district: string
  depot_code: string
  dock_type: string
  parking_constraint: string | null
  van_only: boolean
  is_mall: boolean
  mall_window_open: string | null
  mall_window_close: string | null
  window_open_time: string | null
  window_close_time: string | null
  lat: number | null
  lng: number | null
}
