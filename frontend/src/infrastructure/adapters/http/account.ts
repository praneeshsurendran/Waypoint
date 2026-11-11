import type { AccountApi } from '@/types/api/account'
import type { Settings } from '@/types/models'
import { getUser } from '@/infrastructure/storage/authSession'

export const devicePrefsKey = 'waypoint.account.preferences'

export function devicePreferences(): Partial<Settings> {
  try {
    return JSON.parse(localStorage.getItem(devicePrefsKey) ?? '{}')
  } catch {
    return {}
  }
}

export function createStubAccountApi(): AccountApi {
  return {
    getSettings: async (): Promise<Settings> => ({
      cutoffClosed: false,
      published: false,
      routeStarted: false,
      routeRevision: 0,
      simulatedOffline: false,
      syncOutcome: 'accepted' as const,
      profilePhone: '',
      notifications: true,
      compactRows: false,
      ...devicePreferences(),
      // The name always follows the signed-in account.
      profileName: getUser()?.full_name ?? getUser()?.username ?? '',
    }),
    // Preferences have no server side; they stay on this device.
    updateSettings: async (values: Partial<Settings>) => {
      try {
        localStorage.setItem(devicePrefsKey, JSON.stringify({ ...devicePreferences(), ...values }))
      } catch {
        // Storage can be unavailable; the preference simply is not remembered.
      }
    },
    saveProfilePhoto: async () => {},
  }
}
