import { request } from '@/api/client/apiClient'

/** Backend plans transport; callers supply their typed response projection. */
export function getDraftPlans<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/plans?status=DRAFT', options)
}

/** Backend plans transport; callers supply their typed response projection. */
export function getPublishedPlans<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/plans?status=PUBLISHED', options)
}

/** Backend plans transport; callers supply their typed response projection. */
export function postPlansAutoPlan<T = unknown>(options?: RequestInit): Promise<T> {
  return request<T>('/plans/auto-plan', options)
}

/** Backend plans transport; callers supply their typed response projection. */
export function patchPlans<T = unknown>(id: string | number, options?: RequestInit): Promise<T> {
  return request<T>(`/plans/${id}`, options)
}

/** Backend plans transport; callers supply their typed response projection. */
export function validatePlan<T = unknown>(id: string | number, options?: RequestInit): Promise<T> {
  return request<T>(`/plans/${id}/validate`, options)
}

/** Backend plans transport; callers supply their typed response projection. */
export function publishPlan<T = unknown>(id: string | number, options?: RequestInit): Promise<T> {
  return request<T>(`/plans/${id}/publish`, options)
}
