import { driverWorkspace } from '@/constants/workspaces/driver'

import { lazyPage } from '@/app/router/lazyPage'
import type { RoleModule } from '@/types/navigation'

export const driverModule: RoleModule = {
  ...driverWorkspace,
  routes: [
    {
      path: '/driver/history',
      title: 'Route history',
      component: lazyPage(() =>
        import('@/app/driver/DriverRouteHistoryPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/home',
      title: 'Home',
      component: lazyPage(() => import('@/app/driver/DriverHomePage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/route',
      title: 'Current route',
      component: lazyPage(() =>
        import('@/app/driver/DriverCurrentRoutePage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/delivery',
      title: 'Delivery proof',
      component: lazyPage(() => import('@/app/driver/DriverDeliveryPage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/issues',
      title: 'Issues',
      component: lazyPage(() => import('@/app/driver/DriverIssuePage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/pre-departure',
      title: 'Before you leave',
      component: lazyPage(() =>
        import('@/app/driver/DriverPreDeparturePage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/route/details',
      title: 'Manifest',
      component: lazyPage(() =>
        import('@/app/driver/DriverRouteDetailsPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/navigation',
      title: 'Navigation',
      component: lazyPage(() => import('@/app/driver/DriverNavigationPage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/arrival',
      title: 'Arrived',
      component: lazyPage(() => import('@/app/driver/DriverArrivalPage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/proof/capture',
      title: 'Capture proof',
      component: lazyPage(() =>
        import('@/app/driver/DriverProofCapturePage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/proof/camera-unavailable',
      title: 'Camera access',
      component: lazyPage(() =>
        import('@/app/driver/DriverCameraUnavailablePage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/proof/review',
      title: 'Photo review',
      component: lazyPage(() =>
        import('@/app/driver/DriverProofReviewPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/proof/attached',
      title: 'Photo attached',
      component: lazyPage(() =>
        import('@/app/driver/DriverProofAttachedPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/proof/submit',
      title: 'Submit proof',
      component: lazyPage(() =>
        import('@/app/driver/DriverProofSubmitPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/delivered',
      title: 'Delivered',
      component: lazyPage(() => import('@/app/driver/DriverDeliveredPage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/offline',
      title: 'Offline route',
      component: lazyPage(() => import('@/app/driver/DriverOfflinePage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/sync',
      title: 'Saved records',
      component: lazyPage(() => import('@/app/driver/DriverSyncPage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/driver/route/revision',
      title: 'Route revision',
      component: lazyPage(() =>
        import('@/app/driver/DriverRouteRevisionPage').then((m) => m.default),
      ),
      shell: true,
    },
    {
      path: '/driver/sync/history',
      title: 'Sync history',
      component: lazyPage(() =>
        import('@/app/driver/DriverSyncHistoryPage').then((m) => m.default),
      ),
      shell: true,
    },
  ],
}
