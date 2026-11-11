import type { ReactNode } from 'react'
import { SyncStatus } from '@/components/molecules/store-manager/SyncStatus'
import '@/design-system/features/store.css'

export function StorePage({ children }: { children: ReactNode }) {
  return (
    <div className="sm-page">
      <SyncStatus />
      {children}
    </div>
  )
}
