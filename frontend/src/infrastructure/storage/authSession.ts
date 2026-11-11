import type { ApiUserProfile } from '@/types/api/reference'

export function getToken(): string | null {
  try {
    return localStorage.getItem('waypoint.token')
  } catch {
    return null
  }
}

export const authChangedEvent = 'waypoint:auth-changed'

export const announceAuthChange = () => window.dispatchEvent(new Event(authChangedEvent))

export function setToken(token: string): void {
  try {
    localStorage.setItem('waypoint.token', token)
  } catch {
    /* Preserve operation when storage or the error payload is unavailable. */
  }
  announceAuthChange()
}

export function clearToken(): void {
  try {
    localStorage.removeItem('waypoint.token')
  } catch {
    /* Preserve operation when storage or the error payload is unavailable. */
  }
  announceAuthChange()
}

export function getUser(): ApiUserProfile | null {
  try {
    const raw = localStorage.getItem('waypoint.user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setUser(user: ApiUserProfile): void {
  try {
    localStorage.setItem('waypoint.user', JSON.stringify(user))
  } catch {
    /* Preserve operation when storage or the error payload is unavailable. */
  }
}

export function clearUser(): void {
  try {
    localStorage.removeItem('waypoint.user')
  } catch {
    /* Preserve operation when storage or the error payload is unavailable. */
  }
}
