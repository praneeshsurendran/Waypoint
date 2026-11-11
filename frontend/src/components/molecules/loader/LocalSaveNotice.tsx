import { useConnectivity } from '@/hooks/useConnectivity'
import { Notice } from '@/components/molecules/Common'
import '@/design-system/features/loader.css'

export function LocalSaveNotice() {
  const online = useConnectivity()
  return (
    <Notice
      tone="neutral"
      title={online ? 'Saved on this device · Not synced' : 'Offline · saved on this device'}
    />
  )
}
