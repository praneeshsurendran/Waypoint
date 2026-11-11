import type { Apis } from '@/types/api'
import type { OperationsService } from '@/services/OperationsService'
import { createLocalApis } from '@/infrastructure/adapters/local/localApis'
import { createHttpApis } from '@/infrastructure/adapters/http/createHttpApis'

/**
 * The one place that chooses where data comes from.
 *
 * - When VITE_API_URL is set → the real backend, signed in or not.
 * - Otherwise → the local IndexedDB demo (offline development only).
 */
const realApiInUse = () => !!import.meta.env.VITE_API_URL && import.meta.env.VITE_API_URL !== ''

/**
 * The same choice, made on every call, so it always matches the current configuration.
 */
export function createSwitchableApis(service: OperationsService): Apis {
  const local = createLocalApis(service)
  let http: Apis | undefined
  const current = (): Apis => (realApiInUse() ? (http ??= createHttpApis()) : local)
  return new Proxy({} as Apis, { get: (_target, key) => current()[key as keyof Apis] })
}
