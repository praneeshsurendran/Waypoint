import type { Workspace } from '@/types/models'

export interface Session {
  role: Workspace
  memberId?: string | undefined
  /** The sign-in name, for a real account. */
  username?: string | undefined
  name: string
  initials: string
  depot?: string | undefined
  /** What this person works on: outlet for store managers, vehicle for drivers. */
  outletId?: string | undefined
  vehicleId?: string | undefined
  assignment?: string | undefined
}
