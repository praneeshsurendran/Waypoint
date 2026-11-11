import type { OutboxItem, OutboxRequest } from '@/types/storeOutbox'

/**
 * Changes the store makes while it has no connection. Each one is saved on this device, shown as
 * "waiting to send", and sent in order when the connection returns (`useOutboxSync`). The screens see
 * a waiting change as already made (`applyOutbox`), so the person can carry on working.
 *
 * Kept in localStorage so a change survives closing the tab. A backend replaces nothing here: the
 * requests are sent through the same `OrdersApi` calls as an online change.
 */
const key = 'waypoint.store.outbox'
let items: OutboxItem[] | undefined
const listeners = new Set<() => void>()

export function load(): OutboxItem[] {
  if (items) return items
  try {
    const stored = JSON.parse(localStorage.getItem(key) ?? '[]') as OutboxItem[]
    // A send interrupted by closing the tab starts again.
    items = stored.map((item) =>
      item.status === 'sending' ? { ...item, status: 'waiting' } : item,
    )
  } catch {
    items = []
  }
  return items
}
function save(next: OutboxItem[]) {
  items = next
  try {
    localStorage.setItem(key, JSON.stringify(next))
  } catch {
    // Storage can be blocked; the outbox then lasts as long as the page.
  }
  listeners.forEach((listener) => listener())
}
export function subscribe(listener: () => void) {
  listeners.add(listener)
  const reload = (event?: Event) => {
    if (event instanceof StorageEvent && event.key !== key) return
    items = undefined
    listener()
  }
  // Another tab changed the outbox, or the demo was reset.
  const reset = () => save([])
  window.addEventListener('storage', reload)
  window.addEventListener('waypoint:demo-reset', reset)
  return () => {
    listeners.delete(listener)
    window.removeEventListener('storage', reload)
    window.removeEventListener('waypoint:demo-reset', reset)
  }
}

export function enqueue(outletId: string, request: OutboxRequest, title: string) {
  save([
    ...load(),
    {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      outletId,
      request,
      title,
      createdAt: new Date().toISOString(),
      status: 'waiting',
    },
  ])
}
export function setItem(id: string, patch: Partial<OutboxItem>) {
  save(load().map((item) => (item.id === id ? { ...item, ...patch } : item)))
}
export function removeItem(id: string) {
  save(load().filter((item) => item.id !== id))
}
/** Waiting changes for an outlet, oldest first. */
export const waitingItems = (outletId: string) =>
  load().filter((item) => item.outletId === outletId && item.status === 'waiting')

/** This outlet's unsent changes, oldest first. */
