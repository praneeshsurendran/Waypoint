import { useMutation } from '@tanstack/react-query'
import { getPlanPredictions } from '@/api/endpoints/analytics'
import { getToken } from '@/infrastructure/storage/authSession'

export function usePlanPredictions() {
  const query = useMutation({ mutationFn: getPlanPredictions })
  return { ...query, available: Boolean(getToken()) }
}
