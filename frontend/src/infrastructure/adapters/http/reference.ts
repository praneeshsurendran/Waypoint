import { getUser, authChangedEvent } from '@/infrastructure/storage/authSession'
import * as referenceApi from '@/api/endpoints/reference'
import type { OutletRef } from '@/types/api/responses'

const TTL = 30000
let scope = ''
let expires = 0
function checkScope(): void {
  const user = getUser()
  const next = JSON.stringify([user?.id, user?.role, user?.outlet_id, user?.depot_id])
  if (next !== scope || Date.now() >= expires) {
    outletRefsCache = undefined
    vehicleDepotsCache = undefined
    scope = next
    expires = Date.now() + TTL
  }
}

let outletRefsCache: Promise<Map<string, OutletRef>> | undefined

export function outletReferences(): Promise<Map<string, OutletRef>> {
  checkScope()
  outletRefsCache ??= referenceApi
    .getReferenceOutlets()
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
  checkScope()
  vehicleDepotsCache ??= referenceApi
    .getReferenceVehicles()
    .then((vehicles) => new Map(vehicles.map((v) => [v.vehicle_id, v.depot_code])))
    .catch(() => {
      vehicleDepotsCache = undefined
      return new Map<string, string>()
    })
  return vehicleDepotsCache
}

export function invalidateOutletReferences() {
  outletRefsCache = undefined
  vehicleDepotsCache = undefined
  expires = 0
}

if (typeof window !== 'undefined')
  window.addEventListener(authChangedEvent, invalidateOutletReferences)
