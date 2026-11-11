import {
  AlertTriangle,
  ChartNoAxesCombined,
  LayoutGrid,
  MapPin,
  Package,
  Truck,
} from 'lucide-react'
import type { RoleModule } from '@/types/navigation'
export const dispatcherWorkspace: Omit<RoleModule, 'routes'> = {
  key: 'dispatcher',
  label: 'Dispatcher',
  description: 'Plan, allocate and follow progress.',
  icon: LayoutGrid,
  basePath: '/dispatcher',
  home: '/dispatcher/orders',
  nav: [
    { label: 'Orders', path: '/dispatcher/orders', icon: Package },
    { label: 'Planning', path: '/dispatcher/planning', icon: LayoutGrid },
    { label: 'Deferrals', path: '/dispatcher/deferrals', icon: AlertTriangle },
    { label: 'Fleet', path: '/dispatcher/fleet', icon: Truck },
    { label: 'Live tracking', path: '/dispatcher/tracking', icon: MapPin },
    { label: 'Analytics', path: '/dispatcher/analytics', icon: ChartNoAxesCombined },
  ],
}
