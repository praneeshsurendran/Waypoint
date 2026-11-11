import type { Workspace } from '@/types/models'
import { roleModules } from '@/constants/roleWorkspaces'

export const rolePhotos: Partial<Record<Workspace, string>> = {
  dispatcher: '/images/entry/role-dispatcher.jpg',
  'store-manager': '/images/entry/role-store-manager.jpg',
  loader: '/images/entry/role-loader.jpg',
  driver: '/images/entry/role-driver.jpg',
}

export const fieldRoles = (['dispatcher', 'loader', 'driver', 'store-manager'] as const).map(
  (key) => roleModules.find((module) => module.key === key)!,
)
