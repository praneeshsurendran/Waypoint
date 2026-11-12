import { generatePassword } from '@/schemas/administration/credentials'
import * as adminApi from '@/api/endpoints/admin'
import * as authApi from '@/api/endpoints/auth'
import * as referenceApi from '@/api/endpoints/reference'
import type { ApiAuditRow } from '@/types/api/responses'
import type { TeamApi } from '@/types/api/team'
import type { AuditEntry, MemberActivity, TeamMember, Workspace } from '@/types/models'

import { getUser } from '@/infrastructure/storage/authSession'

import type { ApiOutlet } from '@/types/api/reference'

export const workspaceOf: Record<string, Workspace> = {
  DISPATCHER: 'dispatcher',
  LOADER: 'loader',
  DRIVER: 'driver',
  STORE_MANAGER: 'store-manager',
  ADMIN: 'administration',
}

export const apiRoleOf: Record<Workspace, string> = {
  dispatcher: 'DISPATCHER',
  loader: 'LOADER',
  driver: 'DRIVER',
  'store-manager': 'STORE_MANAGER',
  administration: 'ADMIN',
}

export function whenLabel(iso: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return ''
  return at.toDateString() === new Date().toDateString()
    ? at.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
    : at.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

export const auditTitles: Record<string, string> = {
  USER_CREATED: 'Account created',
  USER_UPDATED: 'Account changed',
  USER_SUSPENDED: 'Account suspended',
  USER_REACTIVATED: 'Account reactivated',
  PASSWORD_RESET: 'Temporary password set',
  OUTLET_CREATED: 'Outlet added',
  VEHICLE_CREATED: 'Vehicle added',
}

export function auditDetail(row: ApiAuditRow): string {
  const after = row.after ?? {}
  const who = typeof after.username === 'string' ? after.username : ''
  const what = typeof after.name === 'string' ? after.name : ''
  const label = `${row.entity_type} ${row.entity_id}`
  return [who || what || label, typeof after.role === 'string' ? after.role : '']
    .filter(Boolean)
    .join(' · ')
}

export function createHttpTeamApi(): TeamApi {
  const unsupported = (what: string) => async (): Promise<never> => {
    throw new Error(
      `${what} is not available yet. Create the account with a temporary password instead.`,
    )
  }

  const users = () => adminApi.getAdminUsers()
  const audit = () => adminApi.getAuditLog()
  const patch = (memberId: string, body: Record<string, unknown>) =>
    adminApi.patchAdminUsers(memberId, { method: 'PATCH', body: body }).then(() => undefined)

  return {
    async listMembers() {
      const role = getUser()?.role ?? ''
      if (role !== 'ADMIN') {
        // Everyone else may only see who receives at each outlet, and only the operating roles.
        if (!['DISPATCHER', 'DRIVER', 'LOADER'].includes(role)) return []
        const managers = await referenceApi.getReferenceStoreManagers().catch(() => [])
        return managers.map((m): TeamMember => ({
          id: String(m.id),
          name: m.full_name,
          email: '',
          role: 'store-manager',
          status: 'Active',
          onRoute: false,
          mobile: m.phone ?? undefined,
          outletId: m.outlet_id ?? undefined,
          assignment: m.outlet_id ?? undefined,
        }))
      }
      const [people, outlets, vehicles] = await Promise.all([
        users(),
        referenceApi.getReferenceOutlets().catch(() => [] as ApiOutlet[]),
        referenceApi.getReferenceVehicles().catch(() => []),
      ])
      const outletDepot = new Map(outlets.map((o) => [o.outlet_id, o.depot_code]))
      const vehicleDepot = new Map(vehicles.map((v) => [v.vehicle_id, v.depot_code]))
      return people.map((u): TeamMember => {
        const depot =
          u.depot_id ??
          (u.outlet_id ? outletDepot.get(u.outlet_id) : undefined) ??
          (u.vehicle_id ? vehicleDepot.get(u.vehicle_id) : undefined)
        return {
          id: String(u.id),
          name: u.full_name,
          email: u.email ?? '',
          role: workspaceOf[u.role] ?? 'dispatcher',
          status: u.is_active ? 'Active' : 'Suspended',
          onRoute: Boolean(u.on_route),
          mobile: u.phone ?? undefined,
          depot,
          assignment:
            u.on_route && u.vehicle_id
              ? `${u.vehicle_id} · Trip ${u.trip_number ?? 1}`
              : (u.outlet_id ?? u.vehicle_id ?? depot),
          vehicleId: u.vehicle_id ?? undefined,
          outletId: u.outlet_id ?? undefined,
          accessState: 'Ready',
          username: u.username,
          joined: u.created_at
            ? new Date(u.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })
            : undefined,
        }
      })
    },
    async listAudit() {
      const rows = await audit()
      return rows.map((row): AuditEntry => ({
        id: String(row.id),
        at: row.at,
        action: auditTitles[row.action] ?? row.action,
        detail: auditDetail(row),
        actor: row.actor ?? 'System',
        recordId: row.entity_type === 'user' ? row.entity_id : undefined,
        recordName: typeof row.after?.username === 'string' ? row.after.username : undefined,
      }))
    },
    async getSummary() {
      const [people, rows] = await Promise.all([users(), audit()])
      const active = people.filter((u) => u.is_active).length
      return {
        total: people.length,
        active,
        invited: 0,
        suspended: people.length - active,
        auditEvents: rows.length,
      }
    },
    async listActivity(memberId): Promise<MemberActivity[]> {
      const rows = await audit()
      return rows
        .filter((row) => row.entity_type === 'user' && row.entity_id === memberId)
        .map((row) => ({
          when: whenLabel(row.at),
          title: auditTitles[row.action] ?? row.action,
          detail: auditDetail(row),
        }))
    },
    invite: unsupported('Invitations by email'),
    inviteByMobile: unsupported('Invitations by mobile'),
    async createUser(user) {
      await adminApi.postAdminUsers({
        method: 'POST',
        body: {
          username: user.username,
          password: user.password,
          full_name: user.name,
          email: user.email,
          phone: user.mobile || null,
          role: apiRoleOf[user.role],
          outlet_id:
            user.role === 'store-manager' ? (/OUT\d+/.exec(user.assignment)?.[0] ?? null) : null,
          vehicle_id: user.role === 'driver' ? (/VEH\d+/.exec(user.assignment)?.[0] ?? null) : null,
          depot_id: user.role === 'loader' || user.role === 'dispatcher' ? user.depot : null,
        },
      })
    },
    completeInvitation: unsupported('Completing an invitation'),
    async resetAccess(memberId, password) {
      const temporary = password ?? generatePassword()
      await adminApi.resetUserPassword(memberId, {
        method: 'POST',
        body: { password: temporary },
      })
    },
    updateContact: (memberId, contact) => {
      const body = { full_name: contact.name, email: contact.email, phone: contact.mobile || null }
      // People change their own details; an administrator changes anyone's.
      return getUser()?.role === 'ADMIN'
        ? patch(memberId, body)
        : authApi.patchAuthMe({ method: 'PATCH', body: body }).then(() => undefined)
    },
    requestAccountChange: unsupported('Account change requests'),
    async changeAssignment(memberId, depot, assignment) {
      const people = await users()
      const person = people.find((u) => String(u.id) === memberId)
      if (!person) throw new Error('That person was not found.')
      if (person.role === 'STORE_MANAGER') {
        return patch(memberId, { outlet_id: /OUT\d+/.exec(assignment)?.[0] ?? assignment.trim() })
      }
      if (person.role === 'DRIVER') {
        return patch(memberId, { vehicle_id: /VEH\d+/.exec(assignment)?.[0] ?? assignment.trim() })
      }
      return patch(memberId, { depot_id: depot })
    },
    reassignTrip: (fromMemberId, toMemberId) =>
      adminApi
        .reassignUserTrip(fromMemberId, {
          method: 'POST',
          body: { to_user_id: Number(toMemberId) },
        })
        .then(() => undefined),
    updateRole: (memberId, role) => patch(memberId, { role: apiRoleOf[role] }),
    suspend: (memberId, _scheduled, reason) => patch(memberId, { is_active: false, reason }),
  }
}
