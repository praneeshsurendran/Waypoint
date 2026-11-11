import { AlertTriangle, Camera, Home, MapPin, Truck, CloudUpload, History } from 'lucide-react'
import { assignedDriverLoad, isAssignedStop } from '@/utils/driverWorkflow'
import type { RoleModule } from '@/types/navigation'
export const driverWorkspace: Omit<RoleModule, 'routes'> = {
  key: 'driver',
  label: 'Driver',
  description: 'Deliver, record and sync.',
  icon: Truck,
  basePath: '/driver',
  home: '/driver/home',
  shell: { compactNav: 'tabs', recoveryLink: false },
  search: {
    placeholder: 'Search assigned outlets or orders',
    find: (snapshot, query) => {
      const load = assignedDriverLoad(snapshot),
        text = query.toLowerCase()
      return snapshot.stops
        .filter(
          (stop) =>
            isAssignedStop(stop, snapshot.orders, load) &&
            `${stop.outlet} ${stop.name} ${stop.orderIds.join(' ')}`.toLowerCase().includes(text),
        )
        .map((stop) => ({
          id: stop.id,
          text: `${stop.outlet} · ${stop.name}`,
          path: `/driver/navigation?stop=${encodeURIComponent(stop.id)}`,
        }))
    },
  },
  nav: [
    { label: 'Home', path: '/driver/home', icon: Home },
    {
      label: 'Current route',
      path: '/driver/route',
      icon: MapPin,
      activePaths: ['/driver/route', '/driver/pre-departure', '/driver/navigation'],
    },
    {
      label: 'Delivery proof',
      path: '/driver/delivery',
      icon: Camera,
      activePaths: ['/driver/delivery', '/driver/arrival', '/driver/proof', '/driver/delivered'],
      availability: (snapshot) => {
        const load = assignedDriverLoad(snapshot)
        const stops = snapshot.stops.filter((item) => isAssignedStop(item, snapshot.orders, load))
        const stop =
          stops.find((item) => item.status === 'Arrived') ??
          stops.find((item) => item.status === 'Proof pending')
        return stop
          ? { path: `/driver/delivery?stop=${encodeURIComponent(stop.id)}` }
          : {
              disabledReason:
                'Available after arrival at an assigned outlet. Past proof is in Saved records.',
            }
      },
    },
    { label: 'Delays & issues', path: '/driver/issues', icon: AlertTriangle },
    { label: 'Saved records', path: '/driver/sync', icon: CloudUpload },
    { label: 'Route history', path: '/driver/history', icon: History },
  ],
}
