import { useVehicleDetails, useDepots } from '@/queries/fleet/useFleetQueries'
import { useMembers as useMembersQuery } from '@/queries/administration/useTeamQueries'

import { lazy, Suspense, useState } from 'react'
import { Truck } from 'lucide-react'
import type { Order, Stop } from '@/types/models'
import { useSession } from '@/hooks/useSession'
import { quantityText } from '@/utils/store-manager/orderView'
import { useOnline } from '@/queries/store-manager/useOnline'
import { useStoreProfile } from '@/queries/store-manager/useStore'
import type { RoutePhase } from '@/components/organisms/store-manager/RouteMap'
import { VehiclePanel } from '@/components/organisms/store-manager/VehiclePanel'

// Leaflet is large, so the map is fetched only when this card is shown.
const RouteMap = lazy(() => import('@/components/organisms/store-manager/RouteMap'))

const phaseOf = (order: Order): RoutePhase =>
  order.status === 'Delivered'
    ? 'delivered'
    : order.status === 'En route'
      ? 'en-route'
      : order.status === 'Scheduled'
        ? 'scheduled'
        : 'pending'

const captions: Record<RoutePhase, (vehicle: string, outlet: string) => [string, string]> = {
  pending: (_, outlet) => [
    `${outlet} · Your outlet`,
    'The route and vehicle appear after dispatch',
  ],
  scheduled: (vehicle) => [`${vehicle} · Your assigned vehicle`, 'Planned route preview'],
  'en-route': (vehicle) => [
    `${vehicle} · Your assigned vehicle`,
    'Live position · This order only',
  ],
  delivered: (vehicle, outlet) => [`${vehicle} · Delivery location`, outlet],
}

/** The map for one order: only this outlet, this order's vehicle and the route between them. */
export function RouteMapCard({
  order,
  stop,
  outletId,
}: {
  order: Order
  stop?: Stop | undefined
  outletId: string
}) {
  const session = useSession()
  const online = useOnline()
  const [open, setOpen] = useState(false)
  // The vehicle's kind and the driver, shown when the vehicle is selected on the map.
  const vehicle = useVehicleDetails(order)
  const members = useMembersQuery()
  const driver = order.vehicleId
    ? members.data?.find((m) => m.role === 'driver' && m.vehicleId === order.vehicleId)?.name
    : undefined
  const phase = phaseOf(order)
  const [title, detail] = captions[phase](order.vehicleId ?? 'Vehicle', outletId)
  // The depot is the one that serves this outlet.
  const { profile } = useStoreProfile()
  const depots = useDepots()
  const depotCode = profile?.depot ?? session.depot
  const depotPoint = depots.data?.find((d) => d.code === depotCode)
  const depotName = depotPoint?.code ?? depotCode ?? ''
  return (
    <section className="sm-map-card" aria-label="Route">
      <div className="sm-map-head">
        <Truck size={20} color="#1E8A57" strokeWidth={1.5} aria-hidden="true" />
        <div>
          <strong>{title}</strong>
          <span>{detail}</span>
        </div>
      </div>
      {stop && depotPoint ? (
        <Suspense fallback={<div className="sm-map sm-map-loading" aria-busy="true" />}>
          <RouteMap
            phase={phase}
            outletId={outletId}
            outlet={[stop.lat, stop.lng]}
            depot={[depotPoint.lat, depotPoint.lng]}
            depotName={depotName}
            vehicleId={order.vehicleId}
            online={online}
            onVehicleSelect={() => setOpen(true)}
            overlay={
              open && order.vehicleId ? (
                <VehiclePanel
                  order={order}
                  stop={stop}
                  vehicle={vehicle.data}
                  driver={driver}
                  depot={depotName}
                  onClose={() => setOpen(false)}
                />
              ) : null
            }
          />
        </Suspense>
      ) : stop && depots.isPending ? (
        <div className="sm-map sm-map-loading" aria-busy="true" />
      ) : (
        <p className="sm-map-offline">
          {stop
            ? `The depot for ${outletId} is not on file yet.`
            : `The location of ${outletId} is not on file yet.`}
        </p>
      )}
      <p className="sm-map-legend">
        {outletId} · {quantityText(order)}
        {order.vehicleId && phase !== 'pending' && ' · Select the vehicle for details'}
      </p>
    </section>
  )
}
