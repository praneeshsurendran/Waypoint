import type { ReactNode } from 'react'
import { Btn } from '@/components/atoms/administration/AdminControls'
import { copyText } from '@/schemas/administration/credentials'
import { toast } from 'sonner'
import type { Paging } from '@/hooks/administration/usePaging'
import '@/design-system/features/admin.css'

export function AdminIntro({
  kicker,
  title,
  lead,
  aside,
}: {
  kicker?: string | undefined
  title: string
  lead?: string | undefined
  aside?: ReactNode | undefined
}) {
  return (
    <header className="ad-intro">
      <div>
        {kicker && <p className="ad-kicker">{kicker}</p>}
        <h1>{title}</h1>
        {lead && <p className="ad-lead">{lead}</p>}
      </div>
      {aside && <div className="ad-intro-aside">{aside}</div>}
    </header>
  )
}

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string
  hint?: string | undefined
  error?: string | undefined
  children: ReactNode
}) {
  return (
    <label className="ad-field">
      <span>{label}</span>
      {children}
      {error ? <small role="alert">{error}</small> : hint ? <small>{hint}</small> : null}
    </label>
  )
}

export function Credential({ label, value }: { label: string; value: string }) {
  return (
    <div className="ad-credential">
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <Btn
        small
        variant="grey"
        aria-label={`Copy ${label.toLowerCase()}`}
        onClick={async () => {
          const copied = await copyText(value)
          if (copied) toast.success(`${label} copied`)
          else toast.error('Copying is not available here')
        }}
      >
        Copy
      </Btn>
    </div>
  )
}

export function Pager({
  paging,
  label,
}: {
  paging: Pick<Paging, 'page' | 'pages' | 'setPage'>
  label: string
}) {
  if (paging.pages <= 1) return null
  return (
    <nav className="ad-pager" aria-label={`${label} pages`}>
      <Btn
        small
        variant="outline"
        disabled={paging.page === 1}
        onClick={() => paging.setPage(paging.page - 1)}
      >
        Previous
      </Btn>
      <span aria-live="polite">
        Page {paging.page} of {paging.pages}
      </span>
      <Btn
        small
        variant="outline"
        disabled={paging.page === paging.pages}
        onClick={() => paging.setPage(paging.page + 1)}
      >
        Next
      </Btn>
    </nav>
  )
}
