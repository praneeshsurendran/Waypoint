import type { ReactNode } from 'react'
import '@/design-system/features/admin.css'

export function AdminPage({ children }: { children: ReactNode }) {
  return <div className="ad-page">{children}</div>
}
