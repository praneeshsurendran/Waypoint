import * as referenceApi from '@/api/endpoints/reference'
import type { OutletRef } from '@/types/api/responses'
import type { ApiOutlet } from '@/types/api/reference'

let outletRefsCache: Promise<Map<string, OutletRef>> | undefined

export function outletReferences(): Promise<Map<string, OutletRef>> {
  outletRefsCache ??= referenceApi
    .getReferenceOutlets<ApiOutlet[]>()
    .then(
      (outlets) =>
        new Map(
          outlets.map((o) => [
            o.outlet_id,
            {
              name: o.name || `${o.brand} ${o.district}`,
              lat: o.lat ?? undefined,
              lng: o.lng ?? undefined,
              window:
                o.window_open_time && o.window_close_time
                  ? `${o.window_open_time.slice(0, 5)}–${o.window_close_time.slice(0, 5)}`
                  : undefined,
            },
          ]),
        ),
    )
    .catch(() => {
      outletRefsCache = undefined
      return new Map<string, OutletRef>()
    })
  return outletRefsCache
}

let vehicleDepotsCache: Promise<Map<string, string>> | undefined

export function vehicleDepots(): Promise<Map<string, string>> {
  vehicleDepotsCache ??= referenceApi
    .getReferenceVehicles<{ vehicle_id: string; depot_code: string }[]>()
    .then((vehicles) => new Map(vehicles.map((v) => [v.vehicle_id, v.depot_code])))
    .catch(() => {
      vehicleDepotsCache = undefined
      return new Map<string, string>()
    })
  return vehicleDepotsCache
}

export function invalidateOutletReferences() {
  outletRefsCache = undefined
}
