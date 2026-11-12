import * as driverApi from '@/api/endpoints/driver'
import * as loadingApi from '@/api/endpoints/loading'
import * as referenceApi from '@/api/endpoints/reference'
import { outletReferences, vehicleDepots } from '@/infrastructure/adapters/http/reference'
import type { LoadingApi } from '@/types/api/loading'
import type { ApiTrip } from '@/types/api/responses'
import type { Load, Stop, Vehicle } from '@/types/models'

import { mapStop } from '@/mappers/operations'

export function mapTripToLoad(trip: ApiTrip, depot?: string, vehicleDepot?: string): Load {
  let localData: {
    loadedCounts?: Record<string, number>
    checks?: { refrigeration: boolean; condition: boolean; restraints: boolean }
    issue?: string
    photoId?: string
    acknowledgedRevision?: number
  } = {}
  try {
    const raw = localStorage.getItem(`waypoint.load.${trip.id}`)
    if (raw) localData = JSON.parse(raw)
  } catch {
    /* Device storage can be unavailable; preserve the current fallback. */
  }

  const stops = trip.stops ?? []
  const isLoaded =
    trip.status === 'LOADED' || trip.status === 'IN_TRANSIT' || trip.status === 'COMPLETED'
  const isReleased =
    trip.status === 'LOADED' || trip.status === 'IN_TRANSIT' || trip.status === 'COMPLETED'

  // Items ordered by reverse sequence for rear-to-front loading
  const items = stops
    .map((s, idx) => {
      const expected = s.total_cases ?? 0
      const loadedCount = localData.loadedCounts?.[s.outlet_id] ?? (isLoaded ? expected : 0)
      return {
        outlet: s.outlet_id,
        name: s.district ? `${s.outlet_id} · ${s.district}` : s.outlet_id,
        expected,
        loaded: loadedCount,
        stop: s.sequence ?? idx + 1,
        district: s.district ?? undefined,
        lat: s.lat ?? undefined,
        lng: s.lng ?? undefined,
        window: s.window_open?.slice(0, 5),
        eta: s.planned_eta
          ? new Date(s.planned_eta).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : undefined,
      }
    })
    .sort((a, b) => b.stop - a.stop)

  const serverOrigin = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(
    /\/api\/v1\/?$/,
    '',
  )

  return {
    id: String(trip.id),
    vehicleId: trip.vehicle_id,
    trip: trip.trip_number,
    revision: 1,
    bay: `Bay ${(trip.trip_number % 8) + 1}`,
    depot: depot ?? vehicleDepot,
    departureTime: trip.planned_depart
      ? new Date(trip.planned_depart).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : undefined,
    acknowledgedRevision: localData.acknowledgedRevision,
    items,
    checks: localData.checks ?? {
      refrigeration: isLoaded,
      condition: isLoaded,
      restraints: isLoaded,
    },
    issue: localData.issue,
    issueResolved: !localData.issue,
    photoId:
      localData.photoId ?? (trip.photo_path ? `${serverOrigin}${trip.photo_path}` : undefined),
    completed: isLoaded,
    released: isReleased,
  }
}

export function createHttpLoadingApi(): LoadingApi {
  return {
    async listLoads(filter = {}) {
      const params = new URLSearchParams()
      if (filter.depot) params.set('depot', filter.depot)
      const query = params.toString() ? `?${params}` : ''
      const [trips, depots] = await Promise.all([
        loadingApi.getLoadingTripsWithDepotFilter(query).catch(() => [] as ApiTrip[]),
        vehicleDepots(),
      ])
      return trips.map((t) => mapTripToLoad(t, filter.depot, depots.get(t.vehicle_id)))
    },

    async getLoad(loadId) {
      if (!loadId) return undefined
      const trip = await loadingApi.getLoadingTrip(loadId).catch(() => null)
      if (!trip) return undefined
      return mapTripToLoad(trip, undefined, (await vehicleDepots()).get(trip.vehicle_id))
    },

    async getWorkspace(loadId, depot) {
      if (!loadId) return undefined
      const trip = await loadingApi.getLoadingTrip(loadId).catch(() => null)
      if (!trip) return undefined

      let vehicle: Vehicle = {
        id: trip.vehicle_id,
        brand: 'Fresh',
        brandRestricted: false,
        type: 'Truck',
        reefer: false,
        weightCapacity: 0,
        volumeCapacity: 0,
        status: 'Loading',
        location: depot ?? '',
        lat: 6.96,
        lng: 79.9,
        updatedMinutes: 0,
      }
      try {
        const v = await referenceApi.getReferenceVehicle(trip.vehicle_id)
        if (v) {
          vehicle = {
            id: v.vehicle_id,
            brand: 'Fresh',
            brandRestricted: false,
            type: v.type?.toLowerCase() === 'van' ? 'Van' : 'Truck',
            reefer: v.is_refrigerated,
            weightCapacity: v.weight_cap_kg,
            volumeCapacity: v.volume_cap_m3,
            status: 'Loading',
            location: v.depot_code,
            lat: 6.96,
            lng: 79.9,
            updatedMinutes: 0,
          }
        }
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }

      const load = mapTripToLoad(trip, depot, (await vehicleDepots()).get(trip.vehicle_id))
      const refs = await outletReferences()
      const stops: Stop[] = (trip.stops ?? []).map((s) => mapStop(s, refs))
      return {
        load,
        vehicle,
        published: true,
        stops,
        weight: trip.planned_weight ?? 0,
        volume: trip.planned_volume ?? 0,
      }
    },

    async acknowledgeRevision(loadId, expectedRevision) {
      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        current.acknowledgedRevision = expectedRevision
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }
    },

    async setLoaded(loadId, outlet, quantity) {
      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        current.loadedCounts = { ...(current.loadedCounts || {}), [outlet]: quantity }
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }

      await loadingApi
        .reportLoadingFlag(loadId, {
          method: 'POST',
          body: { status: 'OK', note: `Loaded ${quantity} cases for ${outlet}` },
        })
        .catch(() => {})
    },

    async setCheck(loadId, check, checked) {
      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        current.checks = { ...(current.checks || {}), [check]: checked }
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }
    },

    async reportIssue(loadId, issue) {
      const desc =
        typeof issue === 'string'
          ? issue
          : `${issue.kind}: ${issue.description || ''} (${issue.affectedCases} cases at ${issue.outlet})`
      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        current.issue = desc
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }

      await loadingApi
        .reportLoadingFlag(loadId, {
          method: 'POST',
          body: { status: 'DAMAGED', note: desc },
        })
        .catch(() => {})
    },

    async resolveIssue(loadId) {
      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        delete current.issue
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }
    },

    async attachPhoto(loadId, file) {
      const form = new FormData()
      form.append('file', file)
      form.append('stop_id', loadId)
      const res = await driverApi
        .postDriverUploads({
          method: 'POST',
          body: form,
        })
        .catch(() => null)

      const serverOrigin = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1').replace(
        /\/api\/v1\/?$/,
        '',
      )

      const photoUrl = res?.path ? `${serverOrigin}${res.path}` : URL.createObjectURL(file)

      try {
        const key = `waypoint.load.${loadId}`
        const current = JSON.parse(localStorage.getItem(key) || '{}')
        current.photoId = photoUrl
        localStorage.setItem(key, JSON.stringify(current))
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }

      if (res?.path) {
        await loadingApi
          .reportLoadingFlag(loadId, {
            method: 'POST',
            body: {
              status: 'OK',
              note: 'Loading proof photograph uploaded',
              photo_path: res.path,
            },
          })
          .catch(() => {})
      }
    },

    async complete(loadId) {
      await loadingApi.releaseLoadingTrip(loadId, { method: 'POST' })
    },
  }
}
