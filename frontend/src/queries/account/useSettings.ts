import { useApiQuery } from '@/queries/useApiQuery'

export function useAccountSettings() {
  return useApiQuery(['account', 'settings'], (api) => api.account.getSettings())
}

export function useDeviceSettings() {
  return useApiQuery(['settings'], (api) => api.account.getSettings())
}
