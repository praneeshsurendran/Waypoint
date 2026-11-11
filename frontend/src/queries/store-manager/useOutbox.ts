import { useSyncExternalStore } from 'react'
import { subscribe, load } from '@/infrastructure/storage/storeOutbox'

export function useOutbox(outletId: string) {
  const all = useSyncExternalStore(subscribe, load)
  return all.filter((item) => item.outletId === outletId)
}
