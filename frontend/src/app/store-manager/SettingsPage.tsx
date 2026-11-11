import { useDeviceSettings } from '@/queries/account/useSettings'
import { useApis } from '@/app/providers/ApisContext'
import { Switch } from '@/components/atoms/switch'
import { ActionLink } from '@/components/atoms/store-manager/StoreControls'
import { Callout, PageIntro } from '@/components/molecules/store-manager/StoreFields'
import { StorePage } from '@/components/templates/store-manager/StorePage'
import { useOutbox } from '@/queries/store-manager/useOutbox'
import { useStoreOutlet } from '@/queries/store-manager/useStore'
import { useStoreAction } from '@/queries/store-manager/useStoreAction'

/** Preferences: notifications, and what is stored on this device. */
export default function SettingsPage() {
  const apis = useApis()
  const action = useStoreAction()
  const outletId = useStoreOutlet()
  const unsent = useOutbox(outletId).length
  const settings = useDeviceSettings()
  if (!settings.data) return null
  return (
    <StorePage>
      <PageIntro title="Preferences" context={`${outletId} · Store manager`} />
      <section className="sm-panel" aria-label="Notifications">
        <h2 className="sm-h22">Notifications</h2>
        <div className="sm-setting">
          <div>
            <strong>Show operational notifications</strong>
            <p className="sm-muted sm-small">
              Deferrals, deliveries and receipts for your outlet. Anything that needs your action
              always appears in Notifications.
            </p>
          </div>
          <Switch
            checked={settings.data.notifications}
            aria-label="Show operational notifications"
            onCheckedChange={(value) =>
              action.run(() => apis.account.updateSettings({ notifications: value }))
            }
          />
        </div>
      </section>
      <section className="sm-panel" aria-label="This device">
        <h2 className="sm-h22">Saved on this device</h2>
        <p className="sm-muted">
          Orders, receipts and reports made without a connection are kept in this browser until they
          are sent. Clearing site data removes anything not yet sent.
        </p>
        {unsent > 0 ? (
          <Callout title={`${unsent} change${unsent === 1 ? '' : 's'} not sent yet`}>
            They are sent automatically when your connection returns.
          </Callout>
        ) : (
          <p className="sm-note">Everything has been sent.</p>
        )}
        <div className="sm-actions">
          <ActionLink variant="outline" to="/store-manager/notifications">
            Back to notifications
          </ActionLink>
        </div>
      </section>
    </StorePage>
  )
}
