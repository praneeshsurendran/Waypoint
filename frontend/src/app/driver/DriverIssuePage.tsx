import { useNavigate } from 'react-router-dom'
import type { ChangeEvent } from 'react'
import { useDriverStop } from '@/queries/driver/useDriverData'
import { DriverScreen } from '@/components/templates/driver/DriverScreen'
import { DriverIssueForm } from '@/components/organisms/driver/DriverIssueForm'
import { DriverStoreContact } from '@/components/organisms/driver/DriverStoreContact'
import { DeliveryWindowNotice } from '@/components/molecules/driver/DeliveryWindowNotice'
import { DriverReportedIssue } from '@/components/organisms/driver/DriverReportedIssue'
import { Field, EmptyState } from '@/components/molecules/Common'

export default function DriverIssuePage() {
  const state = useDriverStop(),
    navigate = useNavigate()
  function selectStop(event: ChangeEvent<HTMLSelectElement>) {
    navigate(`/driver/issues?stop=${encodeURIComponent(event.target.value)}`)
  }
  return (
    <DriverScreen
      title="Delays & delivery issues"
      loading={state.isPending}
      error={state.error}
      retry={() => void state.refetch()}
      description="Report delays, vehicle breakdowns or unsuccessful attempts. Reports keep delivery open; dispatch decides rescheduling or cancellation."
    >
      {!state.stop ? (
        <EmptyState title="No assigned deliveries" />
      ) : (
        <>
          <Field label="Affected stop">
            <select className="native-select" value={state.stop.id} onChange={selectStop}>
              {state.data?.stops.map((stop) => (
                <option key={stop.id} value={stop.id}>
                  {stop.outlet} · {stop.name}
                </option>
              ))}
            </select>
          </Field>
          <DeliveryWindowNotice stop={state.stop} orders={state.data?.orders ?? []} />
          <DriverStoreContact stop={state.stop} />
          <div className="grid grid-cols-1 gap-4 min-[901px]:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
            <DriverIssueForm key={state.stop.id} state={state} />
            <DriverReportedIssue state={state} />
          </div>
        </>
      )}
    </DriverScreen>
  )
}
