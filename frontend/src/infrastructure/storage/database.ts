import type { RouteState } from '@/types/api/delivery'
import type { RouteEvent } from '@/types/routeHistory'
import Dexie, { type Table } from 'dexie'
import type { Evidence, QueuedAction, Snapshot } from '@/types/models'
import type { DriverProofDraft } from '@/types/driverProof'

export class WaypointDatabase extends Dexie {
  snapshots!: Table<{ id: string; data: Omit<Snapshot, 'queue'> }, string>
  evidence!: Table<Evidence, string>
  queue!: Table<QueuedAction, string>
  httpRoutes!: Table<{ actorId: number; route: RouteState }, number>
  httpRouteHistory!: Table<RouteEvent & { actorId?: number | undefined }, string>
  driverProofDrafts!: Table<DriverProofDraft, string>
  constructor(name = 'waypoint-operations-v1') {
    super(name)
    this.version(1).stores({
      snapshots: 'id',
      evidence: 'id,kind,entityId',
      queue: 'id,status,createdAt,evidenceId',
    })
    this.version(2).stores({ driverProofDrafts: 'stopId' })
    this.version(3).stores({ httpRouteHistory: 'id,actorId,at' })
    this.version(4).stores({ httpRoutes: 'actorId' })
  }
}
