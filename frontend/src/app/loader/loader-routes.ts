import { loaderWorkspace } from '@/constants/workspaces/loader'

import { lazyPage } from '@/app/router/lazyPage'
import type { RoleModule } from '@/types/navigation'

const pages = () => import('@/app/loader/LoaderPages')

export const loaderModule: RoleModule = {
  ...loaderWorkspace,
  routes: [
    {
      path: '/loader/queue',
      title: 'Shift dashboard',
      component: lazyPage(() => pages().then((m) => m.LoaderQueuePage)),
      shell: true,
    },
    {
      path: '/loader/loading',
      title: 'Load workspace',
      component: lazyPage(() => pages().then((m) => m.LoaderWorkspacePage)),
      shell: true,
    },
    {
      path: '/loader/proof',
      title: 'Loading proof',
      component: lazyPage(() => pages().then((m) => m.LoaderWorkspacePage), { proofOnly: true }),
      shell: true,
    },
    {
      path: '/loader/loading/:loadId',
      title: 'Load workspace',
      component: lazyPage(() => pages().then((m) => m.LoaderWorkspacePage)),
      shell: true,
    },
    {
      path: '/loader/proof/:loadId',
      title: 'Loading proof',
      component: lazyPage(() => pages().then((m) => m.LoaderWorkspacePage), { proofOnly: true }),
      shell: true,
    },
  ],
}
