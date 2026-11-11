import { Bell, Home, Package, Truck } from 'lucide-react'
import { createElement } from 'react'
import type { RoleModule } from '@/types/navigation'
import { lateOrders } from '@/utils/store-manager/lateness'
import {
  BellFilledIcon,
  BoxIcon,
  GridIcon,
  TruckIcon,
} from '@/components/atoms/store-manager/StoreIcons'
const delivery = '/store-manager/deliveries'
export const storeManagerWorkspace: Omit<RoleModule, 'routes'> = {
  key: 'store-manager',
  label: 'Store Manager',
  description: 'Order, track and confirm receipt.',
  icon: Package,
  basePath: '/store-manager',
  home: '/store-manager/overview',
  nav: [
    {
      label: 'Overview',
      menuLabel: 'Order placement',
      path: '/store-manager/overview',
      icon: Home,
      renderIcon: (active) => createElement(GridIcon, { active }),
    },
    {
      label: 'Orders',
      path: '/store-manager/orders',
      icon: Package,
      renderIcon: (active) => createElement(BoxIcon, { active }),
    },
    {
      label: 'Deliveries',
      menuLabel: 'Delivery tracking',
      path: delivery,
      icon: Truck,
      renderIcon: (active) => createElement(TruckIcon, { active }),
    },
    {
      label: 'Alerts',
      path: '/store-manager/alerts',
      icon: Bell,
      renderIcon: (active) => createElement(BellFilledIcon, { active }),
    },
  ],
  search: {
    placeholder: 'Search orders, deliveries or issues',
    find: (snapshot, query, session) => {
      const text = query.toLowerCase()
      return [...snapshot.orders, ...(snapshot.orderHistory ?? [])]
        .filter((order) => order.outlet === session.outletId)
        .filter((order) =>
          `${order.id} ${order.reference ?? ''} ${order.temperature} ${order.status} ${order.issue ?? ''}`
            .toLowerCase()
            .includes(text),
        )
        .map((order) => ({
          id: order.id,
          text: `${order.reference ?? order.id} · ${order.temperature === 'Chilled' ? 'Fresh / Chilled' : 'Fresh / Dry'} · ${order.status}`,
          path: `/store-manager/orders/${order.id}`,
        }))
    },
  },
  shell: {
    compactBelow: 761,
    compactNav: 'tabs',
    // The store has its own notifications and preferences pages; the profile page is shared.
    accountPaths: {
      profile: '/store-manager/profile',
      settings: '/store-manager/settings',
      notifications: '/store-manager/notifications',
    },
    recoveryLink: false,
    identity: (session) => ({
      title: session.outletId ?? 'Store',
      subtitle: 'Waypoint Group · NoMoreTokens',
    }),
    compactSubtitle: (session) => `Store · ${session.outletId ?? ''}`,
    // Count this outlet's unread delivery updates, deferrals and late arrivals.
    alertCount: (snapshot, session) =>
      snapshot.orders.filter(
        (order) =>
          order.outlet === session.outletId &&
          order.status === 'Deferred' &&
          !order.deferralAcknowledged,
      ).length +
      lateOrders(
        snapshot.orders.filter((order) => order.outlet === session.outletId),
        snapshot.stops,
      ).length +
      (snapshot.deliveryNotices ?? []).filter(
        (notice) => notice.outletId === session.outletId && !notice.readAt,
      ).length,
  },
}
