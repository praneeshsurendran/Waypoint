import type { Brand } from '@/types/outlets'

/** kg and m³ per unit (a case for Fresh, a carton for Style, an item for Tech) and the largest order seen. */
export const unitSizes: Record<Brand, { kg: number; m3: number; max: number }> = {
  Fresh: { kg: 6.9, m3: 0.037, max: 300 },
  Style: { kg: 14.9, m3: 0.24, max: 150 },
  Tech: { kg: 214, m3: 0.71, max: 25 },
}

/** A Tech store may state the weight of its items, within what Tech items weigh (kg an item). */
export const techItemKg = { min: 50, max: 500 }

export function estimateLoad(brand: Brand, units: number) {
  const size = unitSizes[brand]
  return {
    weight: Number((units * size.kg).toFixed(1)),
    volume: Number((units * size.m3).toFixed(3)),
  }
}
