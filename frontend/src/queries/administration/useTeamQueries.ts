import { useApiQuery } from '@/queries/useApiQuery'

export function useMembers() {
  const query = useApiQuery(['members'], (apis) => apis.team.listMembers())
  return { ...query, members: query.data ?? [], loaded: query.data !== undefined }
}

export function useSummary() {
  return useApiQuery(['team-summary'], (apis) => apis.team.getSummary())
}

export function useActivity(memberId: string) {
  return useApiQuery(['activity', memberId], (apis) => apis.team.listActivity(memberId))
}

export function useAudit() {
  const query = useApiQuery(['audit'], (apis) => apis.team.listAudit())
  return { ...query, audit: query.data ?? [], loaded: query.data !== undefined }
}
