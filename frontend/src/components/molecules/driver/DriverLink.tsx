import { Link } from 'react-router-dom'
import type { ComponentProps } from 'react'
import { DriverButton as Button } from '@/components/atoms/driver/DriverButton'

export function DriverLink({
  to,
  children,
  variant = 'default',
}: {
  to: string
  children: React.ReactNode
  variant?: ComponentProps<typeof Button>['variant'] | undefined
}) {
  return (
    <Button asChild variant={variant}>
      <Link to={to}>{children}</Link>
    </Button>
  )
}
