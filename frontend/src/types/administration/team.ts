import type { Workspace } from '@/types/models'

export interface Capability {
  label: string
  /** For each role: yes, no, or a short qualifier ("Own outlet"). */
  access: Record<Workspace, boolean | string>
}
