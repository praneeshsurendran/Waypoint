/** Fail at a missing fixture value instead of hiding it with a non-null assertion. */
export function required<T>(value: T | null | undefined): T {
  if (value === null || value === undefined)
    throw new Error('Required test fixture value is missing')
  return value
}
