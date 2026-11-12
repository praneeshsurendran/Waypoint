import { Link, useLocation } from 'react-router-dom'
import type { NavItem } from '@/types/navigation'
import type { Snapshot } from '@/types/models'
import type { Session } from '@/types/session'

export function WorkspaceNavItem({
  item,
  snapshot,
  session,
  className,
  showIcon = true,
  menuLabel = false,
  onNavigate,
}: {
  item: NavItem
  snapshot?: Snapshot | undefined
  session: Session
  className: string
  showIcon?: boolean | undefined
  menuLabel?: boolean | undefined
  onNavigate?: (() => void) | undefined
}) {
  const location = useLocation()
  const active = (item.activePaths ?? [item.path]).some(
    (path) => location.pathname === path || location.pathname.startsWith(`${path}/`),
  )
  const availability = snapshot ? item.availability?.(snapshot, session) : undefined
  const Icon = item.icon
  const content = (
    <>
      {showIcon && (item.renderIcon ? item.renderIcon(active) : <Icon />)}
      {menuLabel ? (item.menuLabel ?? item.label) : item.label}
    </>
  )
  if (availability?.disabledReason)
    return (
      <span
        className={`${className}${active ? ' active' : ''} opacity-50 cursor-not-allowed`}
        role="link"
        aria-disabled="true"
        aria-current={active ? 'page' : undefined}
        tabIndex={0}
        title={availability.disabledReason}
      >
        {content}
        <span className="sr-only"> · {availability.disabledReason}</span>
      </span>
    )
  return (
    <Link
      to={availability?.path ?? item.path}
      className={`${className}${active ? ' active' : ''}`}
      aria-current={active ? 'page' : undefined}
      onClick={onNavigate}
    >
      {content}
    </Link>
  )
}
