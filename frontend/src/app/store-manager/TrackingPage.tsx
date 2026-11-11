import { orderNumber, kindSlash, kindOf } from '@/utils/store-manager/orderView'
import { useSearchParams } from 'react-router-dom'
import { formatLongDate } from '@/utils/calendar'
import { useAction } from '@/queries/useOperations'
import { useBreadcrumb } from '@/components/molecules/Breadcrumbs'
import { Action, ActionLink, Pill } from '@/components/atoms/store-manager/StoreControls'
import { Callout, PageIntro, Tile } from '@/components/molecules/store-manager/StoreFields'
import { StorePage } from '@/components/templates/store-manager/StorePage'
import { RouteMapCard } from '@/components/organisms/store-manager/RouteMapCard'
import { Timeline } from '@/components/organisms/store-manager/Timeline'
import { deliveredLate, durationText, runningLate } from '@/utils/store-manager/lateness'

import { clock12, windowText12 } from '@/utils/store-manager/timeText'
import { formatTime12 } from '@/schemas/store-manager/windows'
import { deferredOrders, pickActiveOrder, useStoreOrders } from '@/queries/store-manager/useStore'
import { useProof } from '@/queries/store-manager/useProof'
import { StorePendingHandoffs } from '@/components/organisms/store-manager/StorePendingHandoffs'
import { SignedReceipt } from '@/components/organisms/store-manager/SignedReceipt'

/** Delivery tracking for one order: where it is, when it arrives and when to be ready. */
export default function TrackingPage() {
  const [params, setParams] = useSearchParams()
  const action = useAction()
  const { orders, outletId, loaded } = useStoreOrders()
  const order = pickActiveOrder(orders, params.get('order'))
  const proof = useProof(order)
  const deferred = deferredOrders(orders)
  useBreadcrumb([{ label: 'Orders', to: '/store-manager/orders' }, { label: 'Tracking' }])
  if (!loaded) return null
  const alertLink = deferred.length > 0 && (
    <ActionLink variant="grey" to="/store-manager/alerts">
      {deferred.length} order{deferred.length === 1 ? '' : 's'} deferred · View alert
    </ActionLink>
  )
  if (!order)
    return (
      <StorePage>
        <PageIntro title="Delivery tracking" context={outletId} />
        <Callout title="No orders yet">
          Place your orders before the cutoff and their delivery appears here.
        </Callout>
        {alertLink}
      </StorePage>
    )
  // Before the dispatcher publishes the plan there is no vehicle, arrival time or map to show.
  const dispatched = ['Scheduled', 'En route', 'Delivered'].includes(order.status)
  const stop = proof.stop
  const arrival = stop?.eta || order.window
  const delivered = order.status === 'Delivered'
  const late = runningLate(order, stop)
  const wasLate = deliveredLate(order)
  const stamp = (at?: string) => (at ? `${formatLongDate(at)} · ${clock12(at)}` : '')
  const heading = delivered
    ? order.receipt === 'Pending'
      ? 'Delivered · Confirm receipt'
      : 'Delivered'
    : 'Delivery tracking'
  const context = !dispatched
    ? `${outletId} · Waiting for the dispatcher`
    : order.status === 'Scheduled'
      ? `Plan published · ${stamp(order.scheduledAt)}`
      : stamp(delivered ? order.deliveredAt : order.departedAt)
  const live = orders.filter((candidate) => candidate.status !== 'Deferred')
  return (
    <StorePage>
      <PageIntro title={heading} context={context} />
      <StorePendingHandoffs />
      {proof.evidence?.kind === 'delivery' && proof.evidence.managerSignOff && (
        <SignedReceipt
          orderId={orderNumber(order)}
          outletId={outletId}
          evidence={proof.evidence}
          url={proof.url}
        />
      )}
      {late && (
        <Callout
          tone="danger"
          title={`Expected ${durationText(late.minutesLate)} after your window closes`}
        >
          The vehicle is now expected at {formatTime12(late.expected)}; your receiving window ends
          at {formatTime12(late.windowEnd)}. Keep receiving staff available, and tell the dispatcher
          if the goods can no longer be accepted.
        </Callout>
      )}
      <section className="sm-panel sm-progress-top" aria-label="Delivery progress">
        <Timeline order={order} />
      </section>
      <div className="sm-tracking">
        <section className="sm-card sm-arrival" aria-label="Arrival and receiving">
          <div className="sm-arrival-left">
            <Pill tone={delivered ? 'green' : dispatched ? 'orange' : 'amber'}>
              {dispatched ? order.status : 'Awaiting allocation'}
            </Pill>
            {late && <Pill tone="red">Running late</Pill>}
            {live.length > 1 ? (
              <div className="sm-segments" role="group" aria-label="Order">
                {live.map((candidate) => (
                  <Action
                    key={candidate.id}
                    small
                    variant={candidate.id === order.id ? 'primary' : 'outline'}
                    onClick={() => setParams({ order: candidate.id })}
                  >
                    {kindOf(candidate).short}
                  </Action>
                ))}
              </div>
            ) : null}
            <p className="sm-order-line">
              {orderNumber(order)} · {kindSlash(order)}
            </p>
            {delivered ? (
              <Tile
                size="lg"
                tone="success"
                label="Delivered at"
                value={order.deliveredAt ? clock12(order.deliveredAt) : '—'}
              />
            ) : (
              <Tile
                size="lg"
                label={order.status === 'En route' ? 'Expected arrival' : 'Planned arrival'}
                value={dispatched ? formatTime12(arrival) : 'Pending'}
              />
            )}
            <p className="sm-arrival-context">
              {delivered
                ? `${wasLate ? `Arrived ${durationText(wasLate)} after your window closed. ` : ''}Photographic proof is attached.${order.receipt === 'Pending' ? ' Receipt confirmation is still pending.' : ''}`
                : !dispatched
                  ? 'No vehicle or arrival time yet. Both appear after the dispatcher publishes the plan.'
                  : order.status === 'Scheduled'
                    ? 'Vehicle assigned. Live position becomes available after departure.'
                    : `Departed ${order.departedAt ? clock12(order.departedAt) : 'the depot'}. Live position updates when the vehicle reports it.`}
            </p>
          </div>
          <div className="sm-arrival-right">
            <Tile size="md" label="Receiving window" value={windowText12(order)} />
            <Tile
              size="md"
              label="Prepare receiving staff"
              value={`Ready by ${formatTime12(order.window)}`}
            />
            {delivered && order.receipt === 'Pending' ? (
              <ActionLink to={`/store-manager/deliveries/${order.id}/receipt`}>
                Confirm receipt
              </ActionLink>
            ) : delivered && (order.receipt === 'Confirmed' || order.receiptReport) ? (
              <ActionLink
                to={
                  order.receipt === 'Confirmed'
                    ? `/store-manager/deliveries/${order.id}/receipt/confirmed`
                    : `/store-manager/deliveries/${order.id}/issue/submitted`
                }
              >
                View receipt
              </ActionLink>
            ) : !delivered ? (
              <Action
                disabled={action.isPending}
                onClick={() => action.run(async () => {}, 'Delivery status refreshed')}
              >
                {order.status === 'En route' ? 'Refresh delivery status' : 'Refresh tracking'}
              </Action>
            ) : null}
            {alertLink}
          </div>
        </section>
        <RouteMapCard order={order} stop={stop} outletId={outletId} />
      </div>
      <section className="sm-panel sm-progress-compact" aria-label="Order journey">
        <h3>Order journey</h3>
        <Timeline order={order} />
      </section>
    </StorePage>
  )
}
