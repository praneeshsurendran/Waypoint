import type { Load } from '@/types/models'

export const checks: [keyof Load['checks'], string][] = [
  ['refrigeration', 'Refrigeration working for chilled goods'],
  ['condition', 'Goods condition checked'],
  ['restraints', 'Restraints secured and stop order checked'],
]
