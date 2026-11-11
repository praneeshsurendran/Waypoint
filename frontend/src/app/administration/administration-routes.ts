import { administrationWorkspace } from '@/constants/workspaces/administration'

import type { ComponentType } from 'react'
import { lazyPage } from '@/app/router/lazyPage'
import type { RoleModule } from '@/types/navigation'

const route = (path: string, title: string, page: () => Promise<{ default: ComponentType }>) => ({
  path,
  title,
  component: lazyPage(() => page().then((m) => m.default)),
  shell: true,
})

export const administrationModule: RoleModule = {
  ...administrationWorkspace,
  routes: [
    route('/administration/team', 'Team & access', () => import('@/app/administration/TeamPage')),
    // Fixed paths first: the user detail route takes any other id.
    route('/administration/team/new', 'Add user', () => import('@/app/administration/AddUserPage')),
    route(
      '/administration/team/created',
      'Account created',
      () => import('@/app/administration/InvitedPage'),
    ),
    route(
      '/administration/team/:memberId',
      'User',
      () => import('@/app/administration/UserDetailPage'),
    ),
    route(
      '/administration/roles',
      'Roles & access',
      () => import('@/app/administration/RolesPage'),
    ),
    route(
      '/administration/assignments',
      'Assignments',
      () => import('@/app/administration/AssignmentsPage'),
    ),
    route('/administration/outlets', 'Outlets', () => import('@/app/administration/OutletsPage')),
    route(
      '/administration/outlets/new',
      'Add outlet',
      () => import('@/app/administration/AddOutletPage'),
    ),
    route(
      '/administration/outlets/:outletId',
      'Outlet',
      () => import('@/app/administration/OutletDetailPage'),
    ),
    route(
      '/administration/vehicles',
      'Vehicles',
      () => import('@/app/administration/VehiclesPage'),
    ),
    route(
      '/administration/vehicles/new',
      'Add vehicle',
      () => import('@/app/administration/AddVehiclePage'),
    ),
    route(
      '/administration/vehicles/:vehicleId',
      'Vehicle',
      () => import('@/app/administration/VehicleDetailPage'),
    ),
    route('/administration/audit', 'Audit log', () => import('@/app/administration/AuditPage')),
  ],
}
