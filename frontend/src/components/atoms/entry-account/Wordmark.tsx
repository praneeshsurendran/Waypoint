import { Link } from 'react-router-dom'
import '@/design-system/features/entry.css'

export function Wordmark({ to = '/welcome' }: { to?: string | undefined }) {
  return (
    <Link to={to} className="entry-wordmark" aria-label="Waypoint home">
      waypoint
      <span aria-hidden="true" />
    </Link>
  )
}
