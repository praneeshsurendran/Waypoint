/** Wire types are derived from the backend OpenAPI; application view models stay separate. */
import type { paths as IdentityPaths } from '@/types/generated/identity'
import type { paths as NetworkPaths } from '@/types/generated/network'
import type { paths as OperationsPaths } from '@/types/generated/operations'
import type { paths as NotificationPaths } from '@/types/generated/notifications'

type Probes = '/health/live' | '/health/ready'
type Paths = Omit<IdentityPaths, Probes> &
  Omit<NetworkPaths, Probes> &
  Omit<NotificationPaths, Probes> &
  OperationsPaths
type Endpoints = { [P in keyof Paths as P extends `/api/v1${infer Rest}` ? Rest : P]: Paths[P] }
export type ApiPath = keyof Endpoints
export type ApiMethod<P extends ApiPath> = {
  [M in keyof Endpoints[P]]-?: NonNullable<Endpoints[P][M]> extends { responses: object }
    ? M
    : never
}[keyof Endpoints[P]] &
  string
type Operation<P extends ApiPath, M extends ApiMethod<P>> = NonNullable<Endpoints[P][M]>
type Success<R> = R extends { responses: infer Responses }
  ? Responses[Extract<keyof Responses, 200 | 201 | 202 | 204>]
  : never
type JsonContent<R> = R extends { content: { 'application/json': infer Value } } ? Value : void
export type ApiResponse<P extends ApiPath, M extends ApiMethod<P>> = JsonContent<
  Success<Operation<P, M>>
>
export type ApiBody<P extends ApiPath, M extends ApiMethod<P>> =
  Operation<P, M> extends { requestBody: { content: { 'application/json': infer Value } } }
    ? Value
    : Operation<P, M> extends {
          requestBody?: { content: { 'application/json': infer Value } } | undefined
        }
      ? Value
      : never
export type ApiQuery<P extends ApiPath, M extends ApiMethod<P>> =
  Operation<P, M> extends { parameters: { query?: infer Query | undefined } } ? Query : never
/** Undefined object properties are omitted on JSON encoding; null remains an explicit wire value. */
export type JsonInput<T> = T extends readonly (infer Value)[]
  ? JsonInput<Value>[]
  : T extends object
    ? {
        [K in keyof T]:
          JsonInput<T[K]> | (Record<never, never> extends Pick<T, K> ? undefined : never)
      }
    : T
export type ContractOptions<P extends ApiPath, M extends ApiMethod<P>> = Omit<
  RequestInit,
  'body' | 'method'
> & {
  method?: Uppercase<M>
  params?: Record<string, string | number> | undefined
  query?: ApiQuery<P, M> | URLSearchParams | string | undefined
  body?: ([ApiBody<P, M>] extends [never] ? FormData : JsonInput<ApiBody<P, M>>) | undefined
}

/** Public endpoint options require the JSON body whenever OpenAPI requires it. */
export type ApiOptions<P extends ApiPath, M extends ApiMethod<P>> = ContractOptions<P, M> &
  (Operation<P, M> extends { requestBody: { content: { 'application/json': unknown } } }
    ? { body: JsonInput<ApiBody<P, M>> }
    : unknown)
