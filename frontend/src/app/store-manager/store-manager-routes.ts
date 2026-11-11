import { storeManagerWorkspace } from '@/constants/workspaces/store-manager'

import { type ComponentType } from 'react'
import { lazyPage } from '@/app/router/lazyPage'
import type { RoleModule } from '@/types/navigation'

const route = (path: string, title: string, page: () => Promise<{ default: ComponentType }>) => ({
  path,
  title,
  component: lazyPage(() => page().then((m) => m.default)),
  shell: true,
})

const delivery = '/store-manager/deliveries'
const openOrders = '/store-manager/orders/confirmed'

export const storeManagerModule: RoleModule = {
  ...storeManagerWorkspace,
  routes: [
    route(
      '/store-manager/overview',
      'Order placement',
      () => import('@/app/store-manager/OverviewPage'),
    ),
    route('/store-manager/orders', 'Orders', () => import('@/app/store-manager/OrdersPage')),
    route(
      '/store-manager/orders/new',
      'Create orders',
      () => import('@/app/store-manager/CreateOrdersPage'),
    ),
    route(
      '/store-manager/orders/review',
      'Review & confirm',
      () => import('@/app/store-manager/ReviewPage'),
    ),
    route(openOrders, 'Orders confirmed', () => import('@/app/store-manager/ConfirmedPage')),
    route(
      '/store-manager/orders/draft',
      'Draft saved for next run',
      () => import('@/app/store-manager/DraftSavedPage'),
    ),
    route(delivery, 'Tracking', () => import('@/app/store-manager/TrackingPage')),
    route(
      `${delivery}/confirm`,
      'Confirm delivery handoff',
      () => import('@/app/store-manager/StoreHandoffPage'),
    ),
    route(
      `${delivery}/:orderId/receipt`,
      'Confirm receipt',
      () => import('@/app/store-manager/ReceiptPage'),
    ),
    route(
      `${delivery}/:orderId/receipt/confirmed`,
      'Receipt confirmed',
      () => import('@/app/store-manager/ReceiptConfirmedPage'),
    ),
    route(
      `${delivery}/:orderId/issue`,
      'Report a delivery issue',
      () => import('@/app/store-manager/IssuePage'),
    ),
    route(
      `${delivery}/:orderId/issue/submitted`,
      'Issue submitted',
      () => import('@/app/store-manager/IssueSubmittedPage'),
    ),
    route('/store-manager/alerts', 'Alerts', () => import('@/app/store-manager/AlertsPage')),
    route(
      '/store-manager/notifications',
      'Notifications',
      () => import('@/app/store-manager/NotificationsPage'),
    ),
    route('/store-manager/profile', 'Profile', () => import('@/app/entry-account/ProfilePage')),
    route(
      '/store-manager/settings',
      'Preferences',
      () => import('@/app/store-manager/SettingsPage'),
    ),
    // Last: a path parameter, so the fixed paths above (new, review, confirmed, draft) win.
    route(
      '/store-manager/orders/:orderId',
      'Order',
      () => import('@/app/store-manager/OrderDetailPage'),
    ),
  ],
}
