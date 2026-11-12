import type { ReactNode, ButtonHTMLAttributes } from 'react'

import type { LinkProps } from 'react-router-dom'
import { Link } from 'react-router-dom'
import '@/design-system/features/store.css'

export function Pill({
  tone = 'green',
  children,
}: {
  tone?: 'green' | 'orange' | 'red' | 'amber' | undefined
  children: ReactNode
}) {
  return (
    <span className="sm-pill">
      <i className={`sm-dot sm-dot-${tone}`} aria-hidden="true" />
      {children}
    </span>
  )
}

export type Variant = 'primary' | 'grey' | 'outline'

export const classes = (variant: Variant, small?: boolean, className?: string) =>
  ['sm-btn', `sm-btn-${variant}`, small ? 'sm-btn-small' : '', className ?? '']
    .filter(Boolean)
    .join(' ')

export function Action({
  variant = 'primary',
  small,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant | undefined
  small?: boolean | undefined
}) {
  return <button type="button" className={classes(variant, small, className)} {...props} />
}

export function ActionLink({
  variant = 'primary',
  small,
  className,
  ...props
}: LinkProps & { variant?: Variant | undefined; small?: boolean | undefined }) {
  return <Link className={classes(variant, small, className)} {...props} />
}
