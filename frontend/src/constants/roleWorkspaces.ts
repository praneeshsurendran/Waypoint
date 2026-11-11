import { administrationWorkspace } from '@/constants/workspaces/administration'
import { dispatcherWorkspace } from '@/constants/workspaces/dispatcher'
import { driverWorkspace } from '@/constants/workspaces/driver'
import { loaderWorkspace } from '@/constants/workspaces/loader'
import { storeManagerWorkspace } from '@/constants/workspaces/store-manager'

/** Navigation metadata has no page imports, so shared UI cannot pull in routes. */
export const roleModules = [
  dispatcherWorkspace,
  storeManagerWorkspace,
  loaderWorkspace,
  driverWorkspace,
  administrationWorkspace,
]
