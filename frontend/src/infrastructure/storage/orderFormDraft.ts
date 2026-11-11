import type { Edits } from '@/types/store-manager/orderForm'

const KEY = 'waypoint.store.orderForm'

export const empty = (): Edits => ({ values: {}, skipped: {} })

let edits: Edits = read()

const listeners = new Set<() => void>()

function read(): Edits {
  try {
    const stored = JSON.parse(sessionStorage.getItem(KEY) ?? 'null') as Edits | null
    return stored?.values && stored.skipped ? stored : empty()
  } catch {
    return empty()
  }
}

export function write(next: Edits) {
  edits = next
  try {
    sessionStorage.setItem(KEY, JSON.stringify(next))
  } catch {
    // Session storage can be unavailable; the form still works until the page is closed.
  }
  listeners.forEach((listener) => listener())
}

export function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export const getSnapshot = () => edits
