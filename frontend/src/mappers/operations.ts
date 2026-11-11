import type { OrderStatus, Order, Stop, Trip } from '@/types/models'

import type { ApiOrder, ApiStop, OutletRef, ApiTrip } from '@/types/api/responses'

export function mapOrderStatus(s: string): OrderStatus {
  const map: Record<string, OrderStatus> = {
    PLACED: 'Confirmed',
    CONFIRMED: 'Confirmed',
    QUEUED: 'Confirmed',
    PLANNED: 'Allocated',
    LOADED: 'Allocated',
    IN_TRANSIT: 'En route',
    DELIVERED: 'Delivered',
    PARTIAL: 'Delivered',
    FAILED: 'En route',
    DEFERRED: 'Deferred',
    CANCELLED: 'Deferred',
  }
  return (map[s] ?? 'Confirmed') as OrderStatus
}

export function orderStatus(status: string, hasVehicle: boolean, published: boolean): OrderStatus {
  if (status === 'LOADED') return 'Scheduled'
  if (status === 'PLANNED') return published ? 'Scheduled' : 'Allocated'
  const mapped = mapOrderStatus(status)
  return mapped === 'Confirmed' && hasVehicle ? 'Allocated' : mapped
}

export function mapReceiptStatus(status?: string): Order['receipt'] {
  if (status === 'FULL') return 'Confirmed'
  if (status === 'PARTIAL' || status === 'DISPUTED') return 'Issue reported'
  return 'Pending'
}

export function toBackendReason(reason: string): string {
  const map: Record<string, string> = {
    'Insufficient Volume Capacity': 'VOLUME_CAPACITY',
    'Insufficient Weight Capacity': 'WEIGHT_CAPACITY',
    'No Compatible Temperature Capacity': 'TEMP_MISMATCH',
    'Two-Trip Limit Reached': 'TWO_TRIP_LIMIT',
  }
  return map[reason] ?? reason.slice(0, 30)
}

export function toFrontendReason(code?: string): string | undefined {
  if (!code) return undefined
  const map: Record<string, string> = {
    VOLUME_CAPACITY: 'Insufficient Volume Capacity',
    WEIGHT_CAPACITY: 'Insufficient Weight Capacity',
    CAPACITY: 'Insufficient Weight Capacity',
    TEMP_MISMATCH: 'No Compatible Temperature Capacity',
    TWO_TRIP_LIMIT: 'Two-Trip Limit Reached',
    MAX_TRIPS: 'Two-Trip Limit Reached',
    VAN_ONLY: 'Insufficient Volume Capacity',
    FUEL_QUOTA: 'Insufficient Volume Capacity',
  }
  return map[code] ?? code
}

export function mapOrder(o: ApiOrder, published = false): Order {
  // The backend records a deferral without always changing the status, so a reason with no vehicle counts too.
  const isDeferred = o.status === 'DEFERRED' || (!o.vehicle_id && Boolean(o.deferral_reason))
  const isAllocated = !isDeferred && Boolean(o.vehicle_id)
  return {
    id: String(o.id),
    reference: o.reference,
    outlet: o.outlet_id,
    outletName: o.outlet_name ?? o.outlet_id,
    brand: (o.brand as Order['brand']) ?? 'Fresh',
    window: o.window_open ?? '05:00',
    windowEnd: o.window_close ?? '07:30',
    volume: o.total_volume,
    weight: o.total_weight,
    temperature: o.temperature_class === 'AMBIENT' ? 'Ambient' : 'Chilled',
    cases: o.total_cases ?? 0,
    status: isDeferred ? 'Deferred' : orderStatus(o.status, isAllocated, published),
    priority: o.priority,
    vehicleId: o.vehicle_id,
    trip: o.trip,
    deferralReason: toFrontendReason(o.deferral_reason),
    receipt: mapReceiptStatus(o.receipt_status),
    scheduledAt: o.scheduled_at,
    departedAt: o.departed_at,
    deferralAcknowledged: Boolean(o.deferral_acknowledged_at),
    deferralAcknowledgedAt: o.deferral_acknowledged_at,
    receiptReport: o.receipt_report
      ? {
          kind: o.receipt_report.kind as 'Missing' | 'Damaged',
          received: o.receipt_report.received,
          affected: o.receipt_report.affected,
          description: o.receipt_report.description,
          recordedAt: o.receipt_report.recorded_at ?? new Date().toISOString(),
        }
      : undefined,
    placedAt: o.placed_at ?? o.created_at,
    deliveredAt: o.delivered_at,
    deliveryDate: o.delivery_date,
    cancelledAt: o.status === 'CANCELLED' ? (o.updated_at ?? o.created_at) : undefined,
  }
}

export function mapStop(s: ApiStop, refs?: Map<string, OutletRef>): Stop {
  const statusMap: Record<string, Stop['status']> = {
    PENDING: 'Upcoming',
    ARRIVED: 'Arrived',
    COMPLETED: 'Delivered',
    PARTIAL: 'Delivered',
    FAILED: 'Cannot deliver',
  }
  const etaText = s.planned_eta
    ? new Date(s.planned_eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''
  return {
    id: String(s.id),
    outlet: s.outlet_id,
    name: refs?.get(s.outlet_id)?.name ?? s.outlet_id,
    address: s.district ?? '',
    // "open–close": the delivery deadline checks read the end of the range.
    window: s.window_open
      ? s.window_close
        ? `${s.window_open}–${s.window_close}`
        : s.window_open
      : (refs?.get(s.outlet_id)?.window ?? ''),
    eta: etaText,
    lat: s.lat ?? refs?.get(s.outlet_id)?.lat ?? 0,
    lng: s.lng ?? refs?.get(s.outlet_id)?.lng ?? 0,
    orderIds: (s.order_ids ?? []).map(String),
    cases: s.total_cases ?? 0,
    status: (statusMap[s.status] ?? 'Upcoming') as Stop['status'],
    proofId: s.proof_id,
  }
}

export function mapTrip(t: ApiTrip): Trip {
  const statusMap: Record<string, Trip['status']> = {
    PLANNED: 'Planned',
    LOADING: 'Planned',
    LOADED: 'Scheduled',
    IN_TRANSIT: 'En route',
    COMPLETED: 'Complete',
    CANCELLED: 'Complete',
  }
  return {
    id: String(t.id),
    vehicleId: t.vehicle_id,
    number: t.trip_number,
    orderIds: [],
    weight: t.planned_weight ?? 0,
    volume: t.planned_volume ?? 0,
    cases: 0,
    status: (statusMap[t.status] ?? 'Planned') as Trip['status'],
  }
}
