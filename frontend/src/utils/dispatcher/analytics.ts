export function barHeight(value: number, max: number, scale = 180) {
  if (value <= 0 || max <= 0) return 0
  return Math.max(8, (value / max) * scale)
}

export function weekLabel(year: number, week: number) {
  return `Wk ${week} · ${year}`
}
