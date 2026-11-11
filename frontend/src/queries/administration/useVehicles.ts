import { useApiQuery } from '@/queries/useApiQuery'

export function useVehicles() {
  const query = useApiQuery(['vehicles'], (apis) => apis.fleet.listVehicles())
  return { ...query, vehicles: query.data ?? [], loaded: query.data !== undefined }
}
