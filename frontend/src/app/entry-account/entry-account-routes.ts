import { lazyPage } from '@/app/router/lazyPage'
import type { AppModule } from '@/types/navigation'

const account = () => import('@/app/entry-account/AccountPages')

/** Public entry pages (welcome, how it works, login, workspace chooser) and account pages. */
export const entryAccountModule: AppModule = {
  key: 'entry-account',
  routes: [
    {
      path: '/welcome',
      title: 'Welcome',
      component: lazyPage(() => import('@/app/entry-account/HomePage').then((m) => m.default)),
      shell: false,
    },
    {
      path: '/how-it-works',
      title: 'How it works',
      component: lazyPage(() => import('@/app/entry-account/ServicePage').then((m) => m.default)),
      shell: false,
    },
    {
      path: '/login',
      title: 'Sign in',
      component: lazyPage(() => import('@/app/entry-account/LoginPage').then((m) => m.default)),
      shell: false,
    },
    {
      path: '/workspaces',
      title: 'Workspaces',
      component: lazyPage(() =>
        import('@/app/entry-account/WorkspacesPage').then((m) => m.default),
      ),
      shell: false,
    },
    {
      path: '/account/profile',
      title: 'Profile',
      component: lazyPage(() => import('@/app/entry-account/ProfilePage').then((m) => m.default)),
      shell: true,
    },
    {
      path: '/account/settings',
      title: 'Preferences',
      component: lazyPage(() => account().then((m) => m.SettingsPage)),
      shell: true,
    },
    {
      path: '/account/notifications',
      title: 'Notifications',
      component: lazyPage(() => account().then((m) => m.NotificationsPage)),
      shell: true,
    },
  ],
}
