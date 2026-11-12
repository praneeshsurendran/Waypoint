import manifest from '@/api/generated/manifest.json'
import { requestWithStatus } from '@/api/client/apiClient'
import { ApiError } from '@/api/client/apiErrors'
import type { ApiPath, ApiMethod, ApiResponse, ContractOptions } from '@/types/api/contracts'

type ValidatorModule = Record<string, (data: unknown) => boolean>
const loaders: Record<
  'identity' | 'network' | 'operations' | 'notifications',
  () => Promise<ValidatorModule>
> = {
  identity: () => import('@/api/generated/identity.mjs'),
  network: () => import('@/api/generated/network.mjs'),
  operations: () => import('@/api/generated/operations.mjs'),
  notifications: () => import('@/api/generated/notifications.mjs'),
}
function owner(value: string): value is keyof typeof loaders {
  return value in loaders
}

export async function contractRequest<P extends ApiPath, M extends ApiMethod<P>>(
  path: P,
  method: M,
  options: ContractOptions<P, M> = {},
): Promise<ApiResponse<P, M>> {
  const operation = manifest.find((item) => item.path === path && item.method === method)
  if (!operation || !owner(operation.owner))
    throw new ApiError(500, 'MISSING_CONTRACT', 'The API contract is not registered.')
  const validators = await loaders[operation.owner]()
  let address: string = path
  for (const [name, value] of Object.entries(options.params ?? {}))
    address = address.replace(`{${name}}`, encodeURIComponent(String(value)))
  if (address.includes('{'))
    throw new ApiError(400, 'INVALID_REQUEST', 'A required path parameter is missing.')
  const query =
    options.query instanceof URLSearchParams
      ? options.query
      : typeof options.query === 'string'
        ? new URLSearchParams(options.query.replace(/^\?/, ''))
        : new URLSearchParams(
            Object.entries(options.query ?? {})
              .filter(([, value]) => value !== undefined && value !== null)
              .map(([name, value]) => [name, String(value)]),
          )
  if (query.size) address += `?${query}`
  const body =
    options.body instanceof FormData
      ? options.body
      : options.body === undefined
        ? undefined
        : JSON.stringify(options.body)
  if (operation.request && (body !== undefined || operation.bodyRequired)) {
    const input: unknown =
      body === undefined ? undefined : JSON.parse(typeof body === 'string' ? body : 'null')
    const validate = validators[operation.request]
    if (!validate || !validate(input))
      throw new ApiError(422, 'INVALID_REQUEST', 'The request does not match the API contract.')
  }
  const { params: _params, query: _query, body: _body, ...init } = options
  void _params
  void _query
  void _body
  const response = await requestWithStatus(address, {
    ...init,
    method: method.toUpperCase(),
    ...(body === undefined ? {} : { body }),
  })
  const result = response.data
  const responses: Record<string, string | null> = operation.responses
  const name = responses[String(response.status)]
  if (
    !(name === null ? result === undefined : typeof name === 'string' && validators[name]?.(result))
  ) {
    throw new ApiError(
      502,
      'INVALID_RESPONSE',
      'The server response does not match the API contract.',
    )
  }
  // The generated validator and this response type originate from the same OpenAPI operation.
  return result as ApiResponse<P, M>
}
