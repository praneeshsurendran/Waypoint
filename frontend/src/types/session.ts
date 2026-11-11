import type { Workspace } from '@/types/models'

export interface Session {
  role: Workspace
  memberId?: string
  /** The sign-in name, for a real account. */
  username?: string
  name: string
  initials: string
  depot?: string
  /** What this person works on: outlet for store managers, vehicle for drivers. */
  outletId?: string
  vehicleId?: string
  assignment?: string
}
