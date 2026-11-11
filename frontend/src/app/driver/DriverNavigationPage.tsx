import { DriverActions } from '@/components/molecules/driver/DriverActions'
import { useState } from 'react'
import { useDriverStop } from '@/queries/driver/useDriverData'
import { DriverStopLayout } from '@/components/templates/driver/DriverStopLayout'
import { DriverRouteMap } from '@/components/organisms/driver/DriverRouteMap'
import { DriverLink } from '@/components/molecules/driver/DriverLink'
import { navigationInstructions } from '@/constants/driver/navigationInstructions'
import { useApis } from '@/app/providers/ApisContext'
import { useHandoffAction as useDriverAction } from '@/queries/delivery/useHandoffAction'
import { DriverButton as Button } from '@/components/atoms/driver/DriverButton'
import { Panel, Notice } from '@/components/molecules/Common'

export default function DriverNavigationPage() {
  const state = useDriverStop(),
    apis = useApis(),
    action = useDriverAction()
  const [instruction, setInstruction] = useState(0)
  function advanceInstruction() {
    setInstruction((current) => (current + 1) % navigationInstructions.length)
  }
  function confirmParked() {
    if (!state.stop) return
    const stopId = state.stop.id
    action.runAndNavigate(
      () => apis.delivery.arrive(stopId),
      state.href('/driver/arrival'),
      'Arrival and safe parking recorded',
    )
  }
  return (
    <DriverStopLayout state={state} title="Turn-by-turn demo" wide>
      <Notice title="Illustrative navigation">
        Instructions are a fixed demonstration. Use your own navigation service for real directions.
      </Notice>
      <Panel title={navigationInstructions[instruction]}>
        <div className="panel-body flex min-w-0 flex-col gap-4">
          <p>
            Toward {state.stop?.outlet} · ETA {state.stop?.eta}
          </p>
          <Button variant="outline" onClick={advanceInstruction}>
            Next demo instruction
          </Button>
        </div>
      </Panel>
      <DriverRouteMap
        stops={state.data?.stops ?? []}
        stop={state.stop}
        vehicle={state.data?.vehicle}
        offline={!state.online}
      />
      {!state.data?.route.started && (
        <Notice title="Start your route first">
          <p>Complete the load check or start the route to record arrival.</p>
          <div className="flex flex-wrap gap-2 mt-2">
            <Button
              disabled={action.isPending}
              onClick={() => {
                action.run(() => apis.delivery.startRoute(), 'Route started')
              }}
            >
              {action.isPending ? 'Starting route…' : 'Start Route Now'}
            </Button>
            <DriverLink to="/driver/pre-departure" variant="secondary">
              Vehicle checklist
            </DriverLink>
          </div>
        </Notice>
      )}
      <DriverActions>
        {state.stop?.status === 'Upcoming' ? (
          <Button disabled={!state.data?.route.started || action.isPending} onClick={confirmParked}>
            Confirm I’ve parked
          </Button>
        ) : (
          <DriverLink to={state.href('/driver/delivery')}>Open stop handoff</DriverLink>
        )}
        <DriverLink to="/driver/route/details" variant="secondary">
          Route details
        </DriverLink>
        <DriverLink to={state.href('/driver/issues')} variant="secondary">
          Report issue
        </DriverLink>
      </DriverActions>
    </DriverStopLayout>
  )
}
