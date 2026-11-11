import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { snapshotKey } from '@/queries/useOperations'
import { useApis } from '@/app/providers/ApisContext'
import { removeItem, setItem, waitingItems } from '@/infrastructure/storage/storeOutbox'
import { useOutbox } from '@/queries/store-manager/useOutbox'
import { deliver } from '@/services/sendStoreOutbox'
import { useOnline } from '@/queries/store-manager/useOnline'
import { useStoreOutlet } from '@/queries/store-manager/useStore'

const plural = (count: number) => `${count} change${count === 1 ? '' : 's'}`

export function useOutboxSync() {
  const apis = useApis()
  const client = useQueryClient()
  const online = useOnline()
  const outletId = useStoreOutlet()
  const items = useOutbox(outletId)
  const busy = useRef(false)
  const waiting = items.filter((item) => item.status === 'waiting' || item.status === 'sending')

  const flush = useCallback(async () => {
    if (busy.current) return
    busy.current = true
    let sent = 0
    try {
      for (const item of waitingItems(outletId)) {
        setItem(item.id, { status: 'sending' })
        try {
          const result = await deliver(apis, outletId, item.request)
          if (result.status === 'sent') {
            removeItem(item.id)
            sent += 1
          } else setItem(item.id, { status: 'draft', message: result.message })
        } catch (error) {
          setItem(item.id, {
            status: 'failed',
            message: error instanceof Error ? error.message : 'It could not be sent.',
          })
        }
      }
      await client.invalidateQueries({ queryKey: snapshotKey })
      if (sent) toast.success(`${plural(sent)} sent`)
    } finally {
      busy.current = false
    }
  }, [apis, client, outletId])
  const waitingCount = waitingItems(outletId).length
  useEffect(() => {
    if (online && waitingCount) void flush()
  }, [online, waitingCount, flush])

  return {
    items,
    waiting,
    online,
    flush,
    retry: (id: string) => setItem(id, { status: 'waiting', message: undefined }),
    dismiss: removeItem,
  }
}
