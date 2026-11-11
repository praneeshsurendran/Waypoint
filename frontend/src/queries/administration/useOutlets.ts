import { useApiQuery } from '@/queries/useApiQuery'

export function useOutlets() {
  const query = useApiQuery(['outlets'], (apis) => apis.outlets.listOutlets())
  return { ...query, outlets: query.data ?? [], loaded: query.data !== undefined }
}
