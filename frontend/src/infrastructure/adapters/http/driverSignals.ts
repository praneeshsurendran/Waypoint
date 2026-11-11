import type { DriverSignalsApi } from '@/types/api/driverSignals'
import * as driverApi from '@/api/endpoints/driver'
import type { DevicePosition } from '@/types/driverSignals'

export const PENDING_POSITIONS_KEY = 'waypoint.pendingPositions'

export function readPendingPositions(): DevicePosition[] {
  try {
    return JSON.parse(localStorage.getItem(PENDING_POSITIONS_KEY) || '[]') as DevicePosition[]
  } catch {
    return []
  }
}

export function writePendingPositions(positions: DevicePosition[]) {
  try {
    localStorage.setItem(PENDING_POSITIONS_KEY, JSON.stringify(positions))
  } catch {
    // Storage can be blocked; the fix is then kept in memory only until the next attempt.
  }
}

export function toApiPosition(p: DevicePosition) {
  return {
    vehicle_id: p.vehicleId,
    lat: p.lat,
    lng: p.lng,
    accuracy: p.accuracy,
    recorded_at: p.recordedAt,
  }
}

export async function sendPosition(position: DevicePosition) {
  await driverApi.postDriverPositions({
    method: 'POST',
    body: JSON.stringify(toApiPosition(position)),
  })
}

export function createHttpDriverSignalsApi(): DriverSignalsApi {
  return {
    registerPushSubscription: async () => {},
    async recordPosition(position: DevicePosition) {
      // Keep only the latest fix per vehicle. Send anything waiting first, then this fix.
      const waiting = readPendingPositions().filter((p) => p.vehicleId !== position.vehicleId)
      const remaining: DevicePosition[] = []
      for (const p of [...waiting, position]) {
        try {
          await sendPosition(p)
        } catch {
          remaining.push(p)
        }
      }
      writePendingPositions(remaining)
    },
    async pendingPositions() {
      return readPendingPositions()
    },
    listNotices: async () => [],
    acknowledgeNotice: async () => {},
    checkDeliveryWindows: async () => {},
  }
}
