import type { ReactNode } from 'react'
import { CheckIcon, AlertIcon } from '@/components/atoms/store-manager/StoreIcons'

import { Pill } from '@/components/atoms/store-manager/StoreControls'
import { orderNumber, quantityText, windowText } from '@/utils/store-manager/orderView'

import '@/design-system/features/store.css'

export function PageIntro({ title, context }: { title: string; context?: ReactNode | undefined }) {
  return (
    <header className="sm-intro">
      <h1>{title}</h1>
      {context && <p>{context}</p>}
    </header>
  )
}

export function Callout({
  tone = 'warning',
  title,
  children,
}: {
  tone?: 'warning' | 'success' | 'danger' | undefined
  title: string
  children?: ReactNode | undefined
}) {
  return (
    <div className="sm-callout" role={tone === 'danger' ? 'alert' : 'status'}>
      {tone === 'success' ? (
        <CheckIcon />
      ) : (
        <AlertIcon tone={tone === 'danger' ? 'danger' : 'warning'} />
      )}
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
      </div>
    </div>
  )
}

export function Tile({
  label,
  value,
  size = 'md',
  tone,
  big,
}: {
  label: string
  value: ReactNode
  size?: 'sm' | 'md' | 'lg' | undefined
  tone?: 'success' | undefined
  big?: boolean | undefined
}) {
  return (
    <div
      className={`sm-tile sm-tile-${size}${tone ? ` sm-tile-${tone}` : ''}${big ? ' sm-tile-big' : ''}`}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export function FieldInput({
  label,
  error,
  hint,
  ...input
}: {
  label: string
  error?: string | undefined
  hint?: string | undefined
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="sm-field">
      <span>{label}</span>
      <input aria-invalid={Boolean(error)} {...input} />
      {error ? <small role="alert">{error}</small> : hint ? <small>{hint}</small> : null}
    </label>
  )
}

export function StepperField({
  label,
  unit,
  value,
  error,
  narrow,
  onChange,
  onStep,
}: {
  label: string
  /** Keep to a comfortable width when the field has a whole row to itself. */
  narrow?: boolean | undefined
  /** What one step adds, for the button labels: "case". */
  unit: string
  value: string
  error?: string | undefined
  onChange: (value: string) => void
  onStep: (by: number) => void
}) {
  return (
    <div className={`sm-field${narrow ? ' sm-field-narrow' : ''}`}>
      <span id={`stepper-${label}`}>{label}</span>
      <div className="sm-stepper">
        <button type="button" aria-label={`Remove one ${unit}`} onClick={() => onStep(-1)}>
          −
        </button>
        <input
          inputMode="numeric"
          aria-labelledby={`stepper-${label}`}
          aria-invalid={Boolean(error)}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button type="button" aria-label={`Add one ${unit}`} onClick={() => onStep(1)}>
          +
        </button>
      </div>
      {error && <small role="alert">{error}</small>}
    </div>
  )
}

export function ReplaceNotice({
  order,
  change = false,
}: {
  order: {
    id: string
    cases: number
    weight: number
    volume: number
    window: string
    windowEnd?: string | undefined
    brand?: 'Fresh' | 'Style' | 'Tech' | undefined
  }
  /** Tech: the order is being changed and no other order is touched. */
  change?: boolean | undefined
}) {
  const unsent = order.id.startsWith('PENDING')
  return (
    <p className="sm-planned" role="note">
      <Pill tone="amber">
        {change ? 'Changing' : 'Replaces'} {unsent ? 'your unsent order' : orderNumber(order)}
      </Pill>
      <span>
        Currently {quantityText(order)} · window {windowText(order)}.{' '}
        {change
          ? 'Saving changes only this order.'
          : 'Confirming replaces it with what you enter here.'}
      </span>
    </p>
  )
}

export function PlannedNotice({ action = 'Changing' }: { action?: string | undefined }) {
  return (
    <p className="sm-planned" role="note">
      <Pill tone="orange">Already planned</Pill>
      <span>
        The dispatcher has planned this order. {action} it sends it back to be planned again.
      </span>
    </p>
  )
}

export function OfflineNotice({ cutoff }: { cutoff: string }) {
  return (
    <Callout title="You’re offline">
      Your order is saved on this device. Dispatch cannot see it until your connection returns, and
      orders close at {cutoff}, so reconnect before then.
    </Callout>
  )
}
