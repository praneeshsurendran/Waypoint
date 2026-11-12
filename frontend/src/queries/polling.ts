import { ApiError } from '@/api/client/apiErrors'
import { getToken, getUser } from '@/infrastructure/storage/authSession'

const configured = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 15000)
/** Visible operational screens refresh at a bounded, configurable interval. */
export const pollInterval = Number.isFinite(configured)
  ? Math.max(5000, Math.min(configured, 300000))
  : 15000

export function identityKey(): readonly (string | number | null)[] {
  const user = getUser()
  return [user?.id ?? null, user?.role ?? null, user?.outlet_id ?? null, user?.depot_id ?? null]
}

export function retryRead(failures: number, error: Error): boolean {
  return (
    failures < 3 &&
    !(
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      error.status !== 429
    )
  )
}

export function retryDelay(attempt: number, error: Error): number {
  const delay = Math.min(60000, 1000 * 2 ** Math.min(attempt, 6)) * (0.8 + Math.random() * 0.4)
  return Math.max(delay, error instanceof ApiError ? (error.retryAfterSeconds ?? 0) * 1000 : 0)
}

export function nextPoll(failures: number, error: Error | null): number | false {
  if (!getToken() || !navigator.onLine) return false
  if (error instanceof ApiError && [401, 403].includes(error.status)) return false
  return Math.max(
    pollInterval * (0.9 + Math.random() * 0.2),
    failures ? retryDelay(failures, error ?? new Error()) : 0,
  )
}
