import { useQueryClient } from '@tanstack/react-query'
import { useApis } from '@/app/providers/ApisContext'
import { snapshotKey, useAction } from '@/queries/useOperations'
import { enqueue } from '@/infrastructure/storage/storeOutbox'
import { type OutboxRequest } from '@/types/storeOutbox'
import { perform } from '@/services/sendStoreOutbox'
import { useOnline } from '@/queries/store-manager/useOnline'
import { useStoreOutlet } from '@/queries/store-manager/useStore'

/**
 * Like useAction(), plus `runThen`: do the work, wait for every screen's data to refresh, and only
 * then continue (usually navigating). Without the wait, the next screen briefly sees the old
 * order and, for example, sends the person back because receipt "is not confirmed yet".
 *
 * `send` is for changes the store makes: online it is sent now; offline it is saved in the outbox
 * and sent when the connection returns, and the person carries on as if it had gone.
 */
export function useStoreAction() {
  const action = useAction()
  const client = useQueryClient()
  const apis = useApis()
  const online = useOnline()
  const outletId = useStoreOutlet()
  const runThen = (work: () => Promise<unknown>, next: () => void, message?: string) =>
    action.run(async () => {
      await work()
      await client.invalidateQueries({ queryKey: snapshotKey })
      next()
    }, message)
  return {
    ...action,
    runThen,
    send: (request: OutboxRequest, title: string, next: () => void) => {
      if (online) return runThen(() => perform(apis, outletId, request), next)
      enqueue(outletId, request, title)
      next()
    },
  }
}
