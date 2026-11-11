import type { LoginResponse } from '@/types/api/reference'
import { authApi } from '@/api/endpoints/auth'
import { setToken, setUser, clearToken, clearUser } from '@/infrastructure/storage/authSession'

export async function login(username: string, password: string): Promise<LoginResponse> {
  const resp = await authApi.login(username, password)
  setToken(resp.access_token)
  setUser(resp.user)
  return resp
}

export function logout(): void {
  clearToken()
  clearUser()
  try {
    localStorage.removeItem('waypoint.lastRole')
  } catch {
    /* Session cleanup is best effort when storage is blocked. */
  }
}

export { getUser, getToken } from '@/infrastructure/storage/authSession'
