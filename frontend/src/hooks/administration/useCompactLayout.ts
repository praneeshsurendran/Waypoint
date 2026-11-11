import { useState, useEffect } from 'react'

export function useCompactLayout(below = 900) {
  const query = `(max-width: ${below - 1}px)`
  const [compact, setCompact] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const media = window.matchMedia(query)
    const change = () => setCompact(media.matches)
    media.addEventListener('change', change)
    return () => media.removeEventListener('change', change)
  }, [query])
  return compact
}
