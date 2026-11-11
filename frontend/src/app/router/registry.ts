import { administrationModule } from '@/app/administration/administration-routes'
import { dispatcherModule } from '@/app/dispatcher/dispatcher-routes'
import { driverModule } from '@/app/driver/driver-routes'
import { entryAccountModule } from '@/app/entry-account/entry-account-routes'
import { loaderModule } from '@/app/loader/loader-routes'
import { recoveryModule } from '@/app/recovery/recovery-routes'
import { storeManagerModule } from '@/app/store-manager/store-manager-routes'
import type { AppModule, RoleModule } from '@/types/navigation'

/** Role workspaces, in the order the workspace switcher lists them. */
export const roleModules: RoleModule[] = [
  dispatcherModule,
  storeManagerModule,
  loaderModule,
  driverModule,
  administrationModule,
]

/** Every module that contributes routes. */
export const appModules: AppModule[] = [...roleModules, entryAccountModule, recoveryModule]

export const appRoutes = appModules.flatMap((module) => module.routes)
