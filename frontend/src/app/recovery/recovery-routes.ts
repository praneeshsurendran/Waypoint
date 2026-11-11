import { lazyPage } from '@/app/router/lazyPage'
import type { AppModule } from '@/types/navigation'

const recovery = lazyPage(() => import('@/app/recovery/RecoveryPage').then((m) => m.default))

/** Saved-record review and sync, reachable from every workspace. */
export const recoveryModule: AppModule = {
  key: 'recovery',
  routes: [
    { path: '/recovery', title: 'Saved records', component: recovery, shell: true },
    { path: '/recovery/review', title: 'Review updated route', component: recovery, shell: true },
  ],
}
