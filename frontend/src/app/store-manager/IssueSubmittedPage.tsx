import { orderNumber, issueReference } from '@/utils/store-manager/orderView'
import { useState } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { formatLongDate } from '@/utils/calendar'
import { clock12 } from '@/utils/store-manager/timeText'
import { Action, ActionLink, Pill } from '@/components/atoms/store-manager/StoreControls'
import { Callout, PageIntro } from '@/components/molecules/store-manager/StoreFields'
import { StorePage } from '@/components/templates/store-manager/StorePage'
import { ProofDialog } from '@/components/organisms/store-manager/ProofPhoto'

import { receiptDestination } from '@/utils/store-manager/receiptRoutes'
import { useProof } from '@/queries/store-manager/useProof'
import { useStoreOrders } from '@/queries/store-manager/useStore'

/** Issue submitted: the report is open and linked to the order and its delivery photograph. */
export default function IssueSubmittedPage() {
  const { orderId } = useParams()
  const { orders, outletId, loaded } = useStoreOrders()
  const [photo, setPhoto] = useState(false)
  const order = orders.find((candidate) => candidate.id === orderId)
  const proof = useProof(order)
  if (!loaded) return null
  const report = order?.receiptReport
  if (!order || order.status !== 'Delivered')
    return <Navigate to="/store-manager/deliveries" replace />
  if (!report) return <Navigate to={receiptDestination(order)} replace />
  const word = report.kind === 'Missing' ? 'missing' : 'damaged'
  return (
    <StorePage>
      <PageIntro
        title="Issue submitted"
        context={`${orderNumber(order)} · ${outletId} · ${formatLongDate(report.recordedAt)} · ${clock12(report.recordedAt)}`}
      />
      <section className="sm-panel sm-result" aria-label="Issue">
        <Pill tone="amber">Open · Awaiting review</Pill>
        <h2>
          {report.kind === 'Missing' ? 'Missing-item report received.' : 'Damage report received.'}
        </h2>
        <div className="sm-value-row">
          <span>Issue reference</span>
          <strong>{issueReference(order, report.kind)}</strong>
        </div>
        <div className="sm-value-row">
          <span>Recorded receipt</span>
          <strong>
            {report.received} received · {report.affected} {word}
          </strong>
        </div>
        <p className="sm-muted">
          The dispatcher can review the report alongside the delivery record and photo. Follow-up
          will appear against this order.
        </p>
        {order.pendingSync && (
          <Callout title="Saved on this device">
            You are offline. This will be sent automatically when your connection returns.
          </Callout>
        )}
        <Callout title="Receipt recorded with an issue">
          This delivery is not marked as received in full without discrepancies.
        </Callout>
        <div className="sm-actions">
          <Action variant="outline" onClick={() => setPhoto(true)}>
            View delivery photograph
          </Action>
          <ActionLink to="/store-manager/overview">Return to orders</ActionLink>
        </div>
      </section>
      <ProofDialog
        open={photo}
        onClose={() => setPhoto(false)}
        orderId={orderNumber(order)}
        outletId={outletId}
        url={proof.url}
        capturedAt={proof.capturedAt}
        evidence={proof.evidence}
      />
    </StorePage>
  )
}
