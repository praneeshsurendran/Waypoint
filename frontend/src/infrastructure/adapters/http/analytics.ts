import * as analyticsApi from '@/api/endpoints/analytics'
import type { AnalyticsApi, WeekCapacity, DemandWeek } from '@/types/api/analytics'

export function createHttpAnalyticsApi(): AnalyticsApi {
  type ApiDemandWeek = {
    depot: string
    brand: string
    iso_year: number
    iso_week: number
    total_m3: number
    chilled_m3: number
    is_event_week: boolean
    in_test_horizon?: boolean
  }
  type ApiWeekCapacity = {
    depot: string
    iso_year: number
    iso_week: number
    total_m3: number
    chilled_m3: number
    operating_days: number
    vehicles_needed: number
    vehicles_available: number
    reefers_needed: number
    reefers_available: number
    drivers_needed: number
    drivers_available: number
    shortfall_vehicles: number
    shortfall_reefers: number
  }
  const mapCapacity = (c: ApiWeekCapacity): WeekCapacity => ({
    depot: c.depot,
    isoYear: c.iso_year,
    isoWeek: c.iso_week,
    totalM3: c.total_m3,
    chilledM3: c.chilled_m3,
    operatingDays: c.operating_days,
    vehiclesNeeded: c.vehicles_needed,
    vehiclesAvailable: c.vehicles_available,
    reefersNeeded: c.reefers_needed,
    reefersAvailable: c.reefers_available,
    driversNeeded: c.drivers_needed,
    driversAvailable: c.drivers_available,
    shortfallVehicles: c.shortfall_vehicles,
    shortfallReefers: c.shortfall_reefers,
  })
  const mapWeek = (w: ApiDemandWeek): DemandWeek => ({
    depot: w.depot,
    brand: w.brand,
    isoYear: w.iso_year,
    isoWeek: w.iso_week,
    totalM3: w.total_m3,
    chilledM3: w.chilled_m3,
    isEventWeek: w.is_event_week,
    inTestHorizon: w.in_test_horizon,
  })
  return {
    async demandForecast() {
      const body = await analyticsApi.getAnalyticsDemandForecast<{
        method: string
        history: ApiDemandWeek[]
        forecast: ApiDemandWeek[]
        capacity: ApiWeekCapacity[]
        backtest: {
          weeks: string[]
          wape_percent: number | null
          by_depot: Record<string, number | null>
        }
      }>()
      return {
        method: body.method,
        history: body.history.map(mapWeek),
        forecast: body.forecast.map(mapWeek),
        capacity: body.capacity.map(mapCapacity),
        backtest: {
          weeks: body.backtest.weeks,
          wapePercent: body.backtest.wape_percent,
          byDepot: body.backtest.by_depot,
        },
      }
    },
  }
}
