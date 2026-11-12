import * as adminApi from '@/api/endpoints/admin'
import * as driverApi from '@/api/endpoints/driver'
import * as loadingApi from '@/api/endpoints/loading'
import * as referenceApi from '@/api/endpoints/reference'
import { getUser } from '@/infrastructure/storage/authSession'
import type { FleetApi } from '@/types/api/fleet'
import type { ApiDevicePosition, ApiTrip } from '@/types/api/responses'

import type { Vehicle } from '@/types/models'

export const OFFLINE_AFTER_MINUTES = 15

export function minutesSince(iso: string) {
  return Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000))
}

export function createHttpFleetApi(): FleetApi {
  return {
    async listDepots() {
      const depots = await referenceApi.getReferenceDepots().catch(() => [])
      return depots.flatMap((d) =>
        d.lat != null && d.lng != null
          ? [{ code: d.code, name: d.name, lat: d.lat, lng: d.lng }]
          : [],
      )
    },
    async listVehicles() {
      const [vehicles, trips, positions, depots] = await Promise.all([
        referenceApi.getReferenceVehicles().catch(() => []),
        // Trips belong to the operating roles; administrators and stores are refused.
        ['ADMIN', 'STORE_MANAGER'].includes(getUser()?.role ?? '')
          ? Promise.resolve([] as ApiTrip[])
          : loadingApi.getLoadingTrips().catch(() => [] as ApiTrip[]),
        // Only dispatchers and drivers may read vehicle positions; other roles would be refused.
        ['DISPATCHER', 'DRIVER'].includes(getUser()?.role ?? '')
          ? driverApi.getDriverPositionsLatest().catch(() => [] as ApiDevicePosition[])
          : Promise.resolve([] as ApiDevicePosition[]),
        referenceApi
          .getReferenceDepots()
          .catch(() => [] as Array<{ code: string; lat: number | null; lng: number | null }>),
      ])
      const positionByVehicle = new Map(positions.map((p) => [p.vehicle_id, p]))
      const depotByCode = new Map(depots.map((d) => [d.code, d]))

      // A vehicle shows its most active trip: en route beats loading, which beats ready.
      const rank: Record<string, number> = { IN_TRANSIT: 3, LOADING: 2, LOADED: 1 }
      const label: Record<string, string> = {
        IN_TRANSIT: 'En route',
        LOADING: 'Loading',
        LOADED: 'Ready',
      }
      const best = new Map<string, string>()
      for (const t of trips) {
        const current = best.get(t.vehicle_id)
        if ((rank[t.status] ?? 0) > (current ? (rank[current] ?? 0) : 0))
          best.set(t.vehicle_id, t.status)
      }
      const tripStatusByVehicle = new Map(
        [...best].map(([vehicle, status]) => [vehicle, label[status]]),
      )

      return vehicles.map((v): Vehicle => {
        const fix = positionByVehicle.get(v.vehicle_id)
        const minutesOld = fix ? minutesSince(fix.recorded_at) : undefined
        // A device that has stopped reporting is shown offline, with its last known position.
        const offline = minutesOld !== undefined && minutesOld > OFFLINE_AFTER_MINUTES
        return {
          id: v.vehicle_id,
          brand: 'Fresh',
          brandRestricted: false,
          type: v.type === 'van' ? 'Van' : 'Truck',
          reefer: v.is_refrigerated,
          weightCapacity: v.weight_cap_kg,
          volumeCapacity: v.volume_cap_m3,
          status: (offline
            ? 'Offline'
            : (tripStatusByVehicle.get(v.vehicle_id) ?? 'Available')) as Vehicle['status'],
          location: v.depot_code ?? 'Peliyagoda',
          depot: v.depot_code,
          registration: v.registration ?? undefined,
          // No device fix: the depot's own position, or NaN when the depot has no coordinates.
          // NaN keeps the vehicle out of the map rather than drawing it at a made-up point.
          lat: fix?.lat ?? depotByCode.get(v.depot_code ?? '')?.lat ?? Number.NaN,
          lng: fix?.lng ?? depotByCode.get(v.depot_code ?? '')?.lng ?? Number.NaN,
          positionSource: fix ? 'device' : undefined,
          positionUpdatedAt: fix?.recorded_at,
          positionAccuracy: fix?.accuracy,
          updatedMinutes: minutesOld ?? 0,
        }
      })
    },

    async createVehicle(input) {
      const created = await adminApi.postAdminVehicles({
        method: 'POST',
        body: {
          brand: input.brand,
          type: input.type === 'Van' ? 'van' : 'truck',
          is_refrigerated: input.reefer,
          depot_code: input.depot,
          weight_cap_kg: input.weightCapacity,
          volume_cap_m3: input.volumeCapacity,
          registration: input.registration || null,
        },
      })
      const vehicle = await this.getVehicle(created.vehicle_id)
      if (!vehicle) throw new Error('The vehicle was added but could not be read back.')
      return { ...vehicle, brand: input.brand }
    },

    async getVehicle(vehicleId) {
      const v = await referenceApi.getReferenceVehicle(vehicleId).catch(() => null)
      if (!v) return undefined
      return {
        id: v.vehicle_id,
        brand: 'Fresh',
        brandRestricted: false,
        type: v.type === 'van' ? 'Van' : 'Truck',
        reefer: v.is_refrigerated,
        weightCapacity: v.weight_cap_kg,
        volumeCapacity: v.volume_cap_m3,
        status: 'Available',
        location: v.depot_code ?? '',
        depot: v.depot_code,
        registration: v.registration ?? undefined,
        lat: 0,
        lng: 0,
        updatedMinutes: 0,
      }
    },
  }
}
