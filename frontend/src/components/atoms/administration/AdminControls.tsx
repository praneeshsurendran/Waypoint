import type { ReactNode, ButtonHTMLAttributes } from 'react'

import type { LinkProps } from 'react-router-dom'
import { Link } from 'react-router-dom'
import '@/design-system/features/admin.css'

export function Card({
  children,
  label,
  className = '',
}: {
  children: ReactNode
  label?: string
  className?: string
}) {
  return (
    <section className={`ad-card ${className}`} aria-label={label}>
      {children}
    </section>
  )
}

export const CardLabel = ({ children }: { children: ReactNode }) => (
  <p className="ad-card-label">{children}</p>
)

export type Tone = 'green' | 'orange' | 'red' | 'amber' | 'grey'

export function Pill({ tone, children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className="ad-pill">
      {tone && <i className={`ad-dot ad-dot-${tone}`} aria-hidden="true" />}
      {children}
    </span>
  )
}

export type Variant = 'primary' | 'grey' | 'outline' | 'danger'

export const classes = (variant: Variant, small?: boolean, extra?: string) =>
  ['ad-btn', `ad-btn-${variant}`, small ? 'ad-btn-small' : '', extra ?? '']
    .filter(Boolean)
    .join(' ')

export function Btn({
  variant = 'primary',
  small,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; small?: boolean }) {
  return <button type="button" className={classes(variant, small, className)} {...props} />
}

export function LinkBtn({
  variant = 'primary',
  small,
  className,
  ...props
}: LinkProps & { variant?: Variant; small?: boolean }) {
  return <Link className={classes(variant, small, className)} {...props} />
}

export function Avatar({ text, size = 40 }: { text: string; size?: number }) {
  return (
    <span className="ad-avatar" style={{ width: size, height: size, fontSize: size * 0.34 }}>
      {text}
    </span>
  )
}
