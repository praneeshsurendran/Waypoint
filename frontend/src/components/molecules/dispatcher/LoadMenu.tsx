import { useState } from 'react'
import { loadStatusLabel } from '@/utils/dispatcher/loading'
import { ChevronDown } from 'lucide-react'

export function LoadMenu({
  value,
  loads,
  onChange,
}: {
  value: string
  loads: Array<{
    id: string
    vehicleId: string
    trip: number
    released: boolean
    completed: boolean
    issueResolved: boolean
  }>
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const selected = loads.find((load) => load.id === value)
  return (
    <div className="load-menu" onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}>
      <button
        type="button"
        className="load-menu-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        onBlur={(e) => {
          if (!e.currentTarget.parentElement?.contains(e.relatedTarget as Node)) setOpen(false)
        }}
      >
        <span>
          {selected
            ? `${selected.vehicleId} · Trip ${selected.trip} · ${loadStatusLabel(selected)}`
            : 'Select a load'}
        </span>
        <ChevronDown size={16} aria-hidden />
      </button>
      {open && (
        <ul className="load-menu-list" role="listbox">
          <li role="option" aria-selected={!value}>
            <button
              type="button"
              className={`load-menu-option ${!value ? 'selected' : ''}`}
              onClick={() => {
                onChange('')
                setOpen(false)
              }}
            >
              Select a load
            </button>
          </li>
          {loads.map((load) => (
            <li key={load.id} role="option" aria-selected={load.id === value}>
              <button
                type="button"
                className={`load-menu-option ${load.id === value ? 'selected' : ''}`}
                onClick={() => {
                  onChange(load.id)
                  setOpen(false)
                }}
              >
                {load.vehicleId} · Trip {load.trip} · {loadStatusLabel(load)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
