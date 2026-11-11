import { ClipboardList, Link2, Shield, Store, Truck, Users } from 'lucide-react'
import type { RoleModule } from '@/types/navigation'
export const administrationWorkspace: Omit<RoleModule, 'routes'> = {
  key: 'administration',
  label: 'Administration',
  description: 'Manage your team and access.',
  icon: Users,
  basePath: '/administration',
  home: '/administration/team',
  nav: [
    { label: 'Users', menuLabel: 'Team & access', path: '/administration/team', icon: Users },
    { label: 'Roles & access', path: '/administration/roles', icon: Shield },
    { label: 'Assignments', path: '/administration/assignments', icon: Link2 },
    { label: 'Outlets', path: '/administration/outlets', icon: Store },
    { label: 'Vehicles', path: '/administration/vehicles', icon: Truck },
    { label: 'Audit log', path: '/administration/audit', icon: ClipboardList },
  ],
  search: {
    placeholder: 'Search users, roles or outlets',
    find: (snapshot, query) => {
      const text = query.toLowerCase()
      const people = snapshot.members
        .filter((member) =>
          `${member.name} ${member.role} ${member.assignment ?? ''} ${member.mobile ?? ''}`
            .toLowerCase()
            .includes(text),
        )
        .map((member) => ({
          id: member.id,
          text: `${member.name} · ${member.role} · ${member.assignment ?? member.depot ?? ''}`,
          path: `/administration/team/${member.id}`,
        }))
      const outlets = (snapshot.outlets ?? [])
        .filter((outlet) =>
          `${outlet.id} ${outlet.name} ${outlet.district}`.toLowerCase().includes(text),
        )
        .map((outlet) => ({
          id: outlet.id,
          text: `${outlet.id} · ${outlet.name} · ${outlet.brand}`,
          path: `/administration/outlets/${outlet.id}`,
        }))
      const fleet = snapshot.vehicles
        .filter((vehicle) =>
          `${vehicle.id} ${vehicle.registration ?? ''}`.toLowerCase().includes(text),
        )
        .map((vehicle) => ({
          id: vehicle.id,
          text: `${vehicle.id} · ${vehicle.type} · ${vehicle.brand}`,
          path: `/administration/vehicles/${vehicle.id}`,
        }))
      return [...people, ...outlets, ...fleet]
    },
  },
  shell: {
    compactBelow: 900,
    compactNav: 'menu',
    recoveryLink: false,
    identity: () => ({ title: 'Administrator', subtitle: 'Waypoint Group' }),
    compactSubtitle: () => 'Admin',
  },
}
