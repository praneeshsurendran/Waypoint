import { useDemandForecast } from '@/queries/dispatcher/useDispatcherQueries'
import { useState } from 'react'
import { Panel, Notice, EmptyState, Metric } from '@/components/molecules/Common'

import { HISTORY_WEEKS_SHOWN } from '@/constants/analytics'
import type { DemandWeek } from '@/types/api/analytics'

import { weekLabel, barHeight } from '@/utils/dispatcher/analytics'

export function DemandForecastPanel() {
  const query = useDemandForecast()
  const [selectedDepot, setSelectedDepot] = useState<string | null>(null)

  if (query.isPending) {
    return (
      <Panel title="Demand forecast">
        <div className="panel-body">Loading demand forecast…</div>
      </Panel>
    )
  }
  if (query.isError || !query.data) {
    return (
      <Panel title="Demand forecast">
        <div className="panel-body">
          <Notice tone="danger" title="Forecast unavailable">
            Demand history could not be loaded. Check that the API is running.
          </Notice>
        </div>
      </Panel>
    )
  }

  const { history, forecast, method, capacity, backtest } = query.data
  const depots = [...new Set([...history, ...forecast].map((w) => w.depot))].sort()
  if (depots.length === 0) {
    return (
      <Panel title="Demand forecast">
        <EmptyState title="No demand history" description={method} />
      </Panel>
    )
  }
  const depot = selectedDepot && depots.includes(selectedDepot) ? selectedDepot : depots[0]
  const brands = [...new Set([...history, ...forecast].map((w) => w.brand))].sort()

  const weekKeys = (rows: typeof history) =>
    [...new Set(rows.map((w) => `${w.isoYear}-${String(w.isoWeek).padStart(2, '0')}`))].sort()
  const depotHistory = history.filter((w) => w.depot === depot)
  const depotForecast = forecast.filter((w) => w.depot === depot)
  const historyKeys = weekKeys(depotHistory).slice(-HISTORY_WEEKS_SHOWN)
  const forecastKeys = weekKeys(depotForecast)
  const columns = [
    ...historyKeys.map((key) => ({ key, isForecast: false })),
    ...forecastKeys.map((key) => ({ key, isForecast: true })),
  ]

  const lookup = new Map<string, DemandWeek>()
  for (const w of depotHistory)
    lookup.set(`${w.brand}|${w.isoYear}-${String(w.isoWeek).padStart(2, '0')}|h`, w)
  for (const w of depotForecast)
    lookup.set(`${w.brand}|${w.isoYear}-${String(w.isoWeek).padStart(2, '0')}|f`, w)
  const valueOf = (brand: string, key: string, isForecast: boolean) =>
    lookup.get(`${brand}|${key}|${isForecast ? 'f' : 'h'}`)
  const peak = Math.max(
    0,
    ...columns.flatMap((c) => brands.map((b) => valueOf(b, c.key, c.isForecast)?.totalM3 ?? 0)),
  )

  // The planned horizon starts at the first test week; weeks before it only bridge the gap.
  const horizonKeys = weekKeys(depotForecast.filter((w) => w.inTestHorizon))
  const nextKey = horizonKeys[0]
  const nextWeek = depotForecast.filter(
    (w) => `${w.isoYear}-${String(w.isoWeek).padStart(2, '0')}` === nextKey,
  )
  const nextTotal = nextWeek.reduce((n, w) => n + w.totalM3, 0)
  const nextChilled = nextWeek.reduce((n, w) => n + w.chilledM3, 0)
  const nextRow = nextWeek[0]
  const depotCapacity = capacity
    .filter((c) => c.depot === depot)
    .sort((a, b) => a.isoYear - b.isoYear || a.isoWeek - b.isoWeek)
  const nextCapacity = depotCapacity.find(
    (c) => nextRow && c.isoYear === nextRow.isoYear && c.isoWeek === nextRow.isoWeek,
  )

  return (
    <Panel
      title="Demand forecast"
      description="Weekly volume by brand. Faded bars are forecast weeks."
    >
      <div className="panel-body">
        <div className="filter-tabs analytics-toggle" role="group" aria-label="Depot">
          {depots.map((d) => (
            <button
              key={d}
              className={`filter-tab ${depot === d ? 'selected' : ''}`}
              aria-pressed={depot === d}
              onClick={() => setSelectedDepot(d)}
            >
              {d}
            </button>
          ))}
        </div>
        <div className="metrics four">
          <Metric
            label="First planned week"
            value={`${nextTotal.toFixed(1)} m³`}
            detail={nextRow ? weekLabel(nextRow.isoYear, nextRow.isoWeek) : 'No forecast weeks'}
          />
          <Metric
            label="Chilled, next week"
            value={`${nextChilled.toFixed(1)} m³`}
            detail="Fresh only"
          />
          <Metric
            label="Vehicles and drivers, next week"
            value={
              nextCapacity
                ? `${nextCapacity.vehiclesNeeded} of ${nextCapacity.vehiclesAvailable}`
                : '—'
            }
            detail={
              nextCapacity?.shortfallVehicles
                ? `Short by ${nextCapacity.shortfallVehicles}`
                : 'One driver per vehicle'
            }
          />
          <Metric
            label="Reefers needed, next week"
            value={
              nextCapacity
                ? `${nextCapacity.reefersNeeded} of ${nextCapacity.reefersAvailable}`
                : '—'
            }
            detail={
              nextCapacity?.shortfallReefers
                ? `Short by ${nextCapacity.shortfallReefers}`
                : 'Chilled volume, reefers available'
            }
          />
        </div>
        <div className="analytics-legend">
          {brands.map((b) => (
            <span key={b}>
              <i className={`analytics-swatch seg-${b.toLowerCase()}`} /> {b}
            </span>
          ))}
          <span>All values in m³</span>
        </div>
        <div className="window-stack-chart forecast-chart">
          {columns.map((c) => (
            <div className="window-volume-group" key={`${c.key}-${c.isForecast}`}>
              <div className="window-stack">
                {brands.map((b) => {
                  const w = valueOf(b, c.key, c.isForecast)
                  const value = w?.totalM3 ?? 0
                  return (
                    <span
                      key={b}
                      className={`window-stack-part seg-${b.toLowerCase()} ${c.isForecast ? 'is-forecast' : ''}`}
                      title={`${b} · ${value.toFixed(1)} m³${w && w.chilledM3 > 0 ? ` · chilled ${w.chilledM3.toFixed(1)} m³` : ''}${w?.isEventWeek ? ' · payday or festival' : ''}`}
                      style={{ height: `${barHeight(value, peak, 120)}px` }}
                    />
                  )
                })}
              </div>
              <small className="forecast-week-label">
                {c.key.replace(/^(\d+)-(\d+)$/, (_, y, wk) => `Wk ${Number(wk)} · ${y}`)}
              </small>
            </div>
          ))}
        </div>
        {depotCapacity.length > 0 && (
          <div className="table-scroll forecast-table-scroll">
            <table className="data-table forecast-table">
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Operating days</th>
                  <th>Volume, m³</th>
                  <th>Vehicles needed / fleet</th>
                  <th>Reefers needed / fleet</th>
                  <th>Drivers needed / fleet</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {depotCapacity.map((c) => {
                  const short = c.shortfallVehicles + c.shortfallReefers
                  const planned = depotForecast.some(
                    (w) => w.inTestHorizon && w.isoYear === c.isoYear && w.isoWeek === c.isoWeek,
                  )
                  return (
                    <tr
                      key={`${c.isoYear}-${c.isoWeek}`}
                      className={planned ? undefined : 'bridging-row'}
                    >
                      <td>
                        {weekLabel(c.isoYear, c.isoWeek)}
                        {!planned && <small className="bridging-tag"> bridging</small>}
                      </td>
                      <td>{c.operatingDays}</td>
                      <td>{c.totalM3.toFixed(1)}</td>
                      <td>
                        {c.vehiclesNeeded} / {c.vehiclesAvailable}
                      </td>
                      <td>
                        {c.reefersNeeded} / {c.reefersAvailable}
                      </td>
                      <td>
                        {c.driversNeeded} / {c.driversAvailable}
                      </td>
                      <td>{short > 0 ? `Short by ${short}` : 'Within fleet'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <Notice title="How this is calculated" tone="neutral">
          {method}{' '}
          {backtest.wapePercent !== null
            ? `Backtest: ${backtest.wapePercent}% average error on the last ${backtest.weeks.length} known weeks.`
            : 'No backtest data.'}{' '}
          Vehicle figures use volume only, so treat them as a minimum.
        </Notice>
      </div>
    </Panel>
  )
}
