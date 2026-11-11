import { useOperations, useAction, useEvidence } from '@/queries/useOperations'
import { useApis } from '@/app/providers/ApisContext'

import { Notice, EmptyState, Panel, StatusBadge, CapacityBar } from '@/components/molecules/Common'

import { departureErrors } from '@/utils/rules'
import { Button } from '@/components/atoms/button'

import { Truck, ShieldCheck, ArrowRight } from 'lucide-react'

import { Link } from 'react-router-dom'

export function ReleaseLoad({ loadId }: { loadId: string }) {
  const { data } = useOperations(),
    apis = useApis(),
    action = useAction()
  const load = data?.loads.find((load) => load.id === loadId),
    { url } = useEvidence(load?.photoId)
  if (!data) return <Notice title="Loading readiness…" />
  if (!load) return <EmptyState title="Load not found" />
  const vehicle = data.vehicles.find((vehicle) => vehicle.id === load.vehicleId)
  const errors = departureErrors(data, load),
    cases = load.items.reduce((n, i) => n + i.loaded, 0),
    total = load.items.reduce((n, i) => n + i.expected, 0),
    deferred = data.orders.filter((o) => o.status === 'Deferred')
  return (
    <>
      {load.issue && !load.issueResolved && (
        <Notice title="Shortfall requires Dispatcher decision" tone="danger">
          {load.issue}
          <div className="mt-3">
            <Button
              disabled={action.isPending || load.released}
              onClick={() =>
                action.run(
                  () => apis.loading.resolveIssue(load.id),
                  'Replacement approved. Loader must acknowledge the revision and repeat checks.',
                )
              }
            >
              Approve replacement and revise load
            </Button>
          </div>
        </Notice>
      )}
      {errors.length > 0 && !load.released && (
        <Notice title="Awaiting loading evidence">{errors.join(' ')}</Notice>
      )}
      {load.released && (
        <Notice title="Vehicle released for departure" tone="success">
          The Driver workspace can now start the assigned route.
        </Notice>
      )}
      <div className="split-grid">
        <Panel
          title={`${load.vehicleId} · Trip ${load.trip} · ${vehicle?.type ?? 'Vehicle'}`}
          action={
            <StatusBadge>
              {load.released ? 'En route' : errors.length ? 'Held for proof' : 'Ready'}
            </StatusBadge>
          }
        >
          <div className="panel-body">
            <div className="check-row">
              <Truck size={19} />
              <div>
                <strong>Load sequence</strong>
                <small>
                  {cases} / {total} cases reconciled ·{' '}
                  {load.items.map((item) => item.outlet).join(' → ')}
                </small>
              </div>
            </div>
            <div className="check-row">
              <ShieldCheck size={19} />
              <div>
                <strong>Safety checks</strong>
                <small>
                  {Object.values(load.checks).filter(Boolean).length} / 3 confirmed ·{' '}
                  {load.issue && !load.issueResolved
                    ? 'Shortfall unresolved'
                    : 'No unresolved shortfalls'}
                </small>
              </div>
            </div>
            <CapacityBar
              label="Weight"
              used={data.orders
                .filter((o) => o.vehicleId === load.vehicleId && o.trip === load.trip)
                .reduce((n, o) => n + o.weight, 0)}
              total={vehicle?.weightCapacity ?? 1}
              unit="kg"
            />
            <CapacityBar
              label="Volume"
              used={data.orders
                .filter((o) => o.vehicleId === load.vehicleId && o.trip === load.trip)
                .reduce((n, o) => n + o.volume, 0)}
              total={vehicle?.volumeCapacity ?? 1}
              unit="m³"
            />
            <Button
              className="w-full mt-5"
              disabled={!!errors.length || load.released || action.isPending}
              onClick={() =>
                action.run(
                  () => apis.planning.release(load.id),
                  'Departure released in the local workspace',
                )
              }
            >
              {load.released
                ? 'Departure released'
                : `Dispatch ${load.vehicleId} · Trip ${load.trip}`}
            </Button>
          </div>
        </Panel>
        <Panel title="Loader handoff">
          <div className="panel-body">
            {url ? (
              <img src={url} alt="Loading proof attached by the Loader" className="proof-image" />
            ) : (
              <Notice title="Loading photograph not attached">
                The loader must complete checks and attach a clear photograph of the load.
              </Notice>
            )}
            <Link to={`/loader/loading/${load.id}`}>
              <Button variant="outline" className="w-full">
                Open Loader workspace
                <ArrowRight size={16} />
              </Button>
            </Link>
            {load.released && (
              <Link to="/driver/home">
                <Button variant="outline" className="w-full mt-3">
                  Open Driver workspace
                  <ArrowRight size={16} />
                </Button>
              </Link>
            )}
            {deferred.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                  {deferred.length} deferred orders
                </p>
                {deferred.map((o) => (
                  <p key={o.id} style={{ fontSize: 13, color: '#6e737b', marginBottom: 4 }}>
                    {o.outlet} · {o.deferralReason}
                  </p>
                ))}
                <p style={{ fontSize: 12, color: '#6e737b', marginTop: 8 }}>
                  They receive priority on the next run.
                </p>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </>
  )
}
