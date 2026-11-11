import { useOutboxSync } from '@/queries/store-manager/useOutboxSync'
import { Action } from '@/components/atoms/store-manager/StoreControls'
import { AlertIcon } from '@/components/atoms/store-manager/StoreIcons'

const plural = (count: number) => `${count} change${count === 1 ? '' : 's'}`

/**
 * Sends what was saved while offline, as soon as the connection is back, and says what is waiting
 * or needs attention. Shown at the top of every store screen; nothing appears when all is sent.
 */
export function SyncStatus() {
  const { items, waiting, online, flush, retry, dismiss } = useOutboxSync()
  if (!items.length) return null
  const sending = waiting.some((item) => item.status === 'sending')
  return (
    <section className="sm-sync" aria-label="Sending status">
      {waiting.length > 0 && (
        <div className="sm-sync-row" role="status">
          <AlertIcon tone="warning" />
          <div>
            <strong>{sending ? 'Sending…' : `${plural(waiting.length)} waiting to send`}</strong>
            <p>
              {online
                ? 'Sending now.'
                : 'Saved on this device. They are sent automatically when you are back online; dispatch cannot see them until then.'}
            </p>
            <ul>
              {waiting.map((item) => (
                <li key={item.id}>{item.title}</li>
              ))}
            </ul>
          </div>
          {online && !sending && (
            <Action small variant="outline" onClick={() => void flush()}>
              Send now
            </Action>
          )}
        </div>
      )}
      {items
        .filter((item) => item.status === 'failed' || item.status === 'draft')
        .map((item) => (
          <div className="sm-sync-row" role="alert" key={item.id}>
            <AlertIcon tone={item.status === 'failed' ? 'danger' : 'warning'} />
            <div>
              <strong>
                {item.status === 'failed' ? 'Not sent' : 'Kept as a draft'} · {item.title}
              </strong>
              <p>{item.message}</p>
            </div>
            <span className="sm-sync-actions">
              {item.status === 'failed' && (
                <Action
                  small
                  variant="outline"
                  onClick={() => {
                    retry(item.id)
                  }}
                >
                  Try again
                </Action>
              )}
              <Action small variant="grey" onClick={() => dismiss(item.id)}>
                Dismiss
              </Action>
            </span>
          </div>
        ))}
    </section>
  )
}
