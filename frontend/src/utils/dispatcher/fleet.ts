import type { Vehicle, Order, Stop } from '@/types/models'

export function reportingCount(vehicles: Vehicle[]) {
  return vehicles.filter((v) => v.positionSource === 'device' && v.status !== 'Offline').length
}

export function isRunningLate(orders: Order[], stops: Stop[], vehicleId: string) {
  const own = orders.filter((o) => o.vehicleId === vehicleId && o.windowEnd)
  return stops.some(
    (s) =>
      s.status !== 'Delivered' &&
      own.some((o) => s.orderIds.includes(o.id) && s.eta > (o.windowEnd as string)),
  )
}

export function minutesBetween(from: string, to: string) {
  const [fh, fm] = from.split(':').map(Number)
  const [th, tm] = to.split(':').map(Number)
  return th * 60 + tm - (fh * 60 + fm)
}
