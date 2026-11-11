import type { Load } from '@/types/models'

export function loadStatus(load: Load, published: boolean) {
  if (load.released) return 'En route'
  if (!published) return 'Awaiting publication'
  if (!load.issueResolved) return 'Held'
  if (load.acknowledgedRevision !== undefined && load.acknowledgedRevision !== load.revision)
    return 'Review required'
  if (load.completed) return 'Awaiting Dispatcher release'
  return load.items.some((item) => item.loaded > 0) ? 'Loading' : 'Not started'
}
