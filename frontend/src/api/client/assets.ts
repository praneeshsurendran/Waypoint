import { BASE_URL } from '@/api/client/apiClient'
import { getToken } from '@/infrastructure/storage/authSession'

/** Private evidence is authorized at the API; never forward credentials to an external host. */
export async function fetchEvidenceBlob(url: string): Promise<Blob | undefined> {
  const target = new URL(url, window.location.origin)
  const apiOrigin = new URL(BASE_URL, window.location.origin).origin
  const token = target.origin === apiOrigin ? getToken() : undefined
  const response = await fetch(url, {
    ...(token ? { headers: { Authorization: `Bearer ${token}` } } : {}),
    cache: 'no-store',
  })
  return response.ok ? response.blob() : undefined
}
