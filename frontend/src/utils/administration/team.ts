import type { Capability } from '@/types/administration/team'
import type { Workspace, TeamMember } from '@/types/models'

export const roleOrder: Workspace[] = [
  'dispatcher',
  'loader',
  'driver',
  'store-manager',
  'administration',
]

export const roleLabels: Record<Workspace, string> = {
  dispatcher: 'Dispatcher',
  loader: 'Loader',
  driver: 'Driver',
  'store-manager': 'Store manager',
  administration: 'Administrator',
}

export const invitableRoles: { role: Workspace; summary: string }[] = [
  { role: 'dispatcher', summary: 'Plans allocations and decides deferrals. Large screen.' },
  { role: 'loader', summary: 'Loads to the stop sequence. Shared dock tablet.' },
  { role: 'driver', summary: 'Follows the route and records proof. Personal phone.' },
  { role: 'store-manager', summary: 'Places orders and confirms receipt. One outlet.' },
]

export const roleName = (role: Workspace) => roleLabels[role]

export const initials = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]!.toUpperCase())
    .join('')

export const statusOrder = { Active: 0, Invited: 1, Suspended: 2 } as const

export function sortMembers(members: TeamMember[]) {
  return [...members].sort(
    (a, b) =>
      roleOrder.indexOf(a.role) - roleOrder.indexOf(b.role) ||
      statusOrder[a.status] - statusOrder[b.status] ||
      a.name.localeCompare(b.name),
  )
}

export const statusTone = (status: TeamMember['status']) =>
  status === 'Active' ? 'green' : status === 'Invited' ? 'orange' : 'red'

export function lastActive(member: TeamMember) {
  if (member.onRoute) return 'On route'
  if (member.status === 'Invited') return 'Not signed in'
  return member.lastActive ?? '—'
}

export const assignmentText = (member: TeamMember) => member.assignment ?? '—'

export const workspaceText: Record<Workspace, string> = {
  dispatcher: 'Dispatcher · large screen web',
  loader: 'Loader · shared dock tablet',
  driver: 'Driver · mobile web',
  'store-manager': 'Store manager · desktop or phone',
  administration: 'Administrator · web',
}

export const none = {
  dispatcher: false,
  loader: false,
  driver: false,
  'store-manager': false,
  administration: false,
}

export const grant = (
  label: string,
  access: Partial<Record<Workspace, boolean | string>>,
): Capability => ({ label, access: { ...none, ...access } })

export const capabilities: Capability[] = [
  grant('View confirmed order queue', { dispatcher: true, 'store-manager': 'Own outlet' }),
  grant('Allocate orders to vehicles', { dispatcher: true }),
  grant('Publish plan and record deferrals', { dispatcher: true }),
  grant('View route and stop sequence', { dispatcher: true, loader: true, driver: 'Own route' }),
  grant('Confirm loading and flag shortfalls', { loader: true }),
  grant('Record delivery proof', { driver: true }),
  grant('Report a delivery issue', {
    dispatcher: 'Review',
    loader: true,
    driver: true,
    'store-manager': true,
  }),
  grant('Place orders before 4 PM', { 'store-manager': true }),
  grant('Confirm what arrived', { 'store-manager': true }),
  grant('Add, suspend and assign users', { administration: true }),
  grant('View the audit log', { administration: true }),
]

export const roleSummary: Record<Workspace, { will: string[]; willNot: string[] }> = {
  driver: {
    will: [
      'See their route and stop sequence',
      'Record proof of delivery, even offline',
      'Report issues to the Dispatcher',
    ],
    willNot: ['See other drivers or change plans', 'Manage users or roles'],
  },
  dispatcher: {
    will: [
      'Plan allocations and publish deliveries',
      'Review fleet capacity and deferrals',
      'Review reported delivery issues',
    ],
    willNot: ['Record loading or delivery evidence', 'Manage users or roles'],
  },
  loader: {
    will: [
      'Review assigned loads and loading sequence',
      'Reconcile quantities and attach loading proof',
      'Flag shortfalls to the Dispatcher',
    ],
    willNot: ['Publish plans or release vehicles', 'Manage users or roles'],
  },
  'store-manager': {
    will: [
      'Place chilled and dry orders for the assigned outlet',
      'Track deliveries and confirm store receipt',
      'Report missing or damaged goods',
    ],
    willNot: ['Change dispatch plans or other outlets', 'Manage users or roles'],
  },
  administration: {
    will: ['Add, suspend and assign users', 'View the audit log'],
    willNot: ['Allocate, load or deliver'],
  },
}
