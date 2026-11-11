import { realBackend } from '@/constants/realBackend'
import { formatWeekday } from '@/utils/calendar'
import type { BusinessClock } from '@/types/businessClock'
import { cutoffLabel } from '@/utils/store-manager/cutoff'
import { ActionLink } from '@/components/atoms/store-manager/StoreControls'

/** The cutoff countdown (or the locked notice) with the way into ordering. */
export function CutoffPanel({ clock }: { clock: BusinessClock }) {
  return (
    <section className="sm-panel sm-cutoff" aria-label="Order cutoff">
      <div>
        {clock.cutoffPassed ? (
          <>
            <h2>Today’s cutoff has passed</h2>
            <p>
              {formatWeekday(clock.deliveryDate)}’s intake is locked ·{' '}
              {realBackend ? 'Orders now are for' : 'Save a draft for'}{' '}
              {formatWeekday(clock.nextRunDate)}
            </p>
          </>
        ) : (
          <>
            <h2>
              {clock.minutesToCutoff} minute{clock.minutesToCutoff === 1 ? '' : 's'} to place
              tomorrow’s orders
            </h2>
            <p>Daily cutoff · {cutoffLabel(clock.cutoff)} Sri Lanka time</p>
          </>
        )}
      </div>
      <ActionLink small to="/store-manager/orders/new">
        {clock.cutoffPassed && !realBackend ? 'Keep a draft' : 'Create orders'}
      </ActionLink>
    </section>
  )
}
