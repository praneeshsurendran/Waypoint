import { realBackend } from '@/constants/realBackend'
import {
  orderNumber,
  orderKinds,
  quantityText,
  temperatures,
  totals,
} from '@/utils/store-manager/orderView'
import { Navigate, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { formatLongDate } from '@/utils/calendar'
import { useStoreAction } from '@/queries/store-manager/useStoreAction'
import { useBusinessClock } from '@/queries/account/useBusinessClock'
import { Action, ActionLink } from '@/components/atoms/store-manager/StoreControls'
import {
  Callout,
  OfflineNotice,
  PlannedNotice,
  ReplaceNotice,
  PageIntro,
} from '@/components/molecules/store-manager/StoreFields'
import { StorePage } from '@/components/templates/store-manager/StorePage'
import { parseForm } from '@/schemas/store-manager/orderForm'
import { useOrderForm } from '@/hooks/store-manager/useOrderForm'

import { useOnline } from '@/queries/store-manager/useOnline'
import { cutoffLabel } from '@/utils/store-manager/cutoff'
import { useStoreOrders, useStoreProfile } from '@/queries/store-manager/useStore'

/** Review & confirm: one last look at the orders before they are recorded as demand. */
export default function ReviewPage() {
  const navigate = useNavigate()
  const action = useStoreAction()
  const clock = useBusinessClock()
  const online = useOnline()
  const { orders, outletId, loaded, byTemperature } = useStoreOrders('next')
  const { profile } = useStoreProfile()
  const form = useOrderForm(orders)
  const parsed = parseForm(form.values, form.included, profile?.window)
  if (!loaded) return null
  if (!parsed.valid || (clock.cutoffPassed && !realBackend))
    return <Navigate to="/store-manager/orders/new" replace />
  const sum = totals(parsed.inputs)
  const confirm = () =>
    action.send(
      { kind: 'orders', inputs: parsed.inputs },
      `Confirm ${sum.orders} Fresh order${sum.orders === 1 ? '' : 's'}`,
      () => {
        form.reset()
        navigate('/store-manager/orders/confirmed')
      },
    )
  const checkCutoff = () => {
    if (clock.cutoffPassed && !realBackend) navigate('/store-manager/orders/new')
    else
      toast(
        `Orders are still open · ${clock.minutesToCutoff} minute${clock.minutesToCutoff === 1 ? '' : 's'} left.`,
      )
  }
  return (
    <StorePage>
      <PageIntro
        title="Review & confirm"
        context={`${sum.orders === 1 ? '1 Fresh order' : `${sum.orders} separate Fresh orders`} · ${outletId} · ${formatLongDate(clock.orderDate)}`}
      />
      {!online && <OfflineNotice cutoff={cutoffLabel(clock.cutoff)} />}
      <section className="sm-panel" aria-label="Orders to confirm">
        <h2>Everything ready for tomorrow?</h2>
        <p className="sm-muted">
          {sum.cases} cases · {sum.weight} kg · {sum.volume} m³ across{' '}
          {sum.orders === 1 ? 'one Fresh order record' : 'two Fresh order records'}
        </p>
        {parsed.inputs.map((input) => {
          const kind = orderKinds[input.temperature]
          return (
            <div className="sm-review-row" key={input.temperature}>
              <div>
                <strong>{kind.title}</strong>
                <small>{kind.subtitle}</small>
                {byTemperature(input.temperature) && (
                  <ReplaceNotice order={byTemperature(input.temperature)!} />
                )}
                {byTemperature(input.temperature)?.status === 'Allocated' && <PlannedNotice />}
              </div>
              <span className="sm-details">{quantityText(input)}</span>
              <span className="sm-window">
                {input.window}–{input.windowEnd}
              </span>
            </div>
          )
        })}
        {temperatures
          .filter((temperature) => !form.included[temperature])
          .map((temperature) => {
            const kind = orderKinds[temperature]
            const existing = byTemperature(temperature)
            return (
              <p className="sm-note" key={temperature}>
                Not included: {kind.title}
                {existing ? ` · your order ${orderNumber(existing)} stays as it is.` : '.'}
              </p>
            )
          })}
      </section>
      <Callout title="Allocation follows the cutoff">
        Confirming records demand. A vehicle and ETA become available after the dispatcher publishes
        the plan.
      </Callout>
      <div className="sm-actions">
        <Action onClick={confirm} disabled={action.isPending}>
          Confirm {sum.orders} order{sum.orders === 1 ? '' : 's'}
        </Action>
        <ActionLink variant="outline" to="/store-manager/orders/new">
          Edit quantities
        </ActionLink>
        <Action variant="outline" onClick={checkCutoff}>
          Check cutoff status
        </Action>
      </div>
    </StorePage>
  )
}
