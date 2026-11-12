import * as driverApi from '@/api/endpoints/driver'
import * as notificationsApi from '@/api/endpoints/notifications'
import type { DriverSignalsApi } from '@/types/api/driverSignals'
import type { DeliveryNotice, DevicePosition } from '@/types/driverSignals'

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
    body: toApiPosition(position),
  })
}

export function createHttpDriverSignalsApi(): DriverSignalsApi {
  return {
    async registerPushSubscription(subscription) {
      await notificationsApi.registerPushSubscription(subscription)
    },
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
    async listNotices(outletId) {
      const rows = await notificationsApi.listNotifications()
      const kinds: Record<string, DeliveryNotice['kind']> = {
        'delivery.started': 'enRoute',
        'delivery.delayed': 'deadline',
        'delivery.failed': 'issue',
        'stop.completed': 'arrival',
        'proof_of_delivery.recorded': 'completed',
        'order.deferred': 'delay',
        'receipt.issue_reported': 'issue',
      }
      return rows
        .filter((row) => !outletId || row.data.outlet_id === outletId)
        .map((row) => ({
          id: row.id,
          key: row.id,
          stopId: String(row.data.stop_id ?? ''),
          outletId: row.data.outlet_id ?? '',
          kind: kinds[row.type] ?? 'completed',
          title: row.type.replaceAll('.', ' ').replaceAll('_', ' '),
          message:
            row.data.note ?? row.data.decision?.reason_code ?? 'Your delivery status has changed.',
          createdAt: row.created_at,
          readAt: row.read ? row.created_at : undefined,
          delivery: 'sent' as const,
        }))
    },
    async acknowledgeNotice(id) {
      await notificationsApi.readNotification(id)
    },
    async checkDeliveryWindows() {
      await notificationsApi.checkDeliveryWindows()
    },
  }
}
