import { dispatcherWorkspace } from '@/constants/workspaces/dispatcher'

import { lazyPage } from '@/app/router/lazyPage'
import type { RoleModule } from '@/types/navigation'

const planning = () => import('@/app/dispatcher/PlanningPages')
const fleet = () => import('@/app/dispatcher/FleetPages')

export const dispatcherModule: RoleModule = {
  ...dispatcherWorkspace,
  routes: [
    {
      path: '/dispatcher/orders',
      title: 'Orders',
      component: lazyPage(() => import('@/app/dispatcher/OrderQueuePage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/dispatcher/planning',
      title: 'Planning',
      component: lazyPage(() => planning().then((m) => m.AllocationPage)),
      shell: true,
    },
    {
      path: '/dispatcher/deferrals',
      title: 'Deferrals',
      component: lazyPage(() => planning().then((m) => m.DeferralsPage)),
      shell: true,
    },
    {
      path: '/dispatcher/review',
      title: 'Review',
      component: lazyPage(() => planning().then((m) => m.ReviewPage)),
      shell: true,
    },
    {
      path: '/dispatcher/release',
      title: 'Release',
      component: lazyPage(() => planning().then((m) => m.ReleasePage)),
      shell: true,
    },
    {
      path: '/dispatcher/fleet',
      title: 'Fleet',
      component: lazyPage(() => fleet().then((m) => m.FleetPage)),
      shell: true,
    },
    {
      path: '/dispatcher/tracking',
      title: 'Live tracking',
      component: lazyPage(() => fleet().then((m) => m.FleetPage), { tracking: true }),
      shell: true,
    },
    {
      path: '/dispatcher/analytics',
      title: 'Analytics',
      component: lazyPage(() => fleet().then((m) => m.AnalyticsPage)),
      shell: true,
    },
  ],
}
