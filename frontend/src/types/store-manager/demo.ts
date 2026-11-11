/** Demo states for the store's orders, so every store screen can be opened without the other roles. */
export type StoreDemoState =
  'confirmed' | 'allocated' | 'scheduled' | 'en-route' | 'late' | 'delivered' | 'received' | 'issue'
