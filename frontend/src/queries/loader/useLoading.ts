import { useApiQuery } from '@/queries/useApiQuery'
import type { Session } from '@/types/session'

export function useLoadingQueue(session: Pick<Session, 'depot'>) {
  return useApiQuery(['loading', 'queue', session.depot], async (apis) => {
    if (!session.depot) return { loads: [], published: false }
    const loads = await apis.loading.listLoads({ depot: session.depot })
    const status = await apis.orders.getIntakeStatus()
    return { loads, published: status.published }
  })
}

export function useLoadingWorkspace(loadId: string, session: Pick<Session, 'depot'>) {
  return useApiQuery(['loading', 'workspace', loadId, session.depot], async (apis) =>
    session.depot ? ((await apis.loading.getWorkspace(loadId, session.depot)) ?? null) : null,
  )
}
