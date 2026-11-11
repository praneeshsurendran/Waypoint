import { useDeviceSettings } from '@/queries/account/useSettings'
import { useConnectivity } from '@/hooks/useConnectivity'

/** True when the device is online and the demo's "Simulate offline" switch is off. */
export function useOnline() {
  const connected = useConnectivity()
  const settings = useDeviceSettings()
  return connected && !settings.data?.simulatedOffline
}
