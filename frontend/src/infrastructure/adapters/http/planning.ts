import * as ordersApi from '@/api/endpoints/orders'
import * as plansApi from '@/api/endpoints/plans'
import * as deferralsApi from '@/api/endpoints/deferrals'
import * as loadingApi from '@/api/endpoints/loading'
import type { PlanningApi } from '@/types/api/planning'
import type { ApiPlan, ApiOrder } from '@/types/api/responses'
import { mapTrip, mapOrder, toBackendReason } from '@/mappers/operations'

import type { Order } from '@/types/models'

export function createHttpPlanningApi(): PlanningApi {
  return {
    async getPlan() {
      const [intakeResp, draftPlans, pubPlans] = await Promise.all([
        ordersApi
          .getOrdersIntakeStatus<{ cutoff_closed: boolean; published: boolean }>()
          .catch(() => ({ cutoff_closed: false, published: false })),
        plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[]),
        plansApi.getPublishedPlans<ApiPlan[]>().catch(() => [] as ApiPlan[]),
      ])

      const plan = draftPlans[0] ?? pubPlans[0]
      const trips = plan?.trips.map(mapTrip) ?? []
      const orders = await ordersApi
        .getOrdersWithDateFilter<ApiOrder[]>(
          plan?.delivery_date ? `?date=${plan.delivery_date}` : '',
        )
        .then((os) => os.map((o) => mapOrder(o)))
        .catch(() => [] as Order[])

      let isReviewed = plan?.status === 'PUBLISHED'
      if (plan && !isReviewed) {
        try {
          isReviewed = localStorage.getItem(`waypoint.plan.reviewed.${plan.id}`) === 'true'
        } catch {
          /* Device storage can be unavailable; preserve the current fallback. */
        }
      }

      return {
        orders,
        trips,
        status: {
          cutoffClosed: intakeResp.cutoff_closed,
          published: intakeResp.published,
          allocationReviewed: isReviewed,
        },
      }
    },

    async autoAllocate() {
      await plansApi.postPlansAutoPlan({ method: 'POST' })
      const plans = await plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[])
      if (plans[0]) {
        try {
          localStorage.removeItem(`waypoint.plan.reviewed.${plans[0].id}`)
        } catch {
          /* Device storage can be unavailable; preserve the current fallback. */
        }
      }
    },

    async allocate(orderId, vehicleId, trip) {
      const plans = await plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[])
      const plan = plans[0]
      if (!plan) throw new Error('No draft plan to edit')
      const targetTrip = plan.trips.find(
        (t) => t.vehicle_id === vehicleId && t.trip_number === trip,
      )
      if (!targetTrip) throw new Error('Trip not found')
      try {
        localStorage.removeItem(`waypoint.plan.reviewed.${plan.id}`)
      } catch {
        /* Device storage can be unavailable; preserve the current fallback. */
      }
      await plansApi.patchPlans(plan.id, {
        method: 'PATCH',
        body: JSON.stringify({ moves: [{ order_id: Number(orderId), to_trip_id: targetTrip.id }] }),
      })
    },

    async unallocate(orderId) {
      const plans = await plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[])
      const plan = plans[0]
      // Say so rather than reporting success for a removal that never happened.
      if (!plan) throw new Error('No draft plan to edit. A published plan cannot be changed.')
      try {
        localStorage.removeItem(`waypoint.plan.reviewed.${plan.id}`)
      } catch {
        // Storage can be blocked; the review flag is re-read from the server anyway.
      }
      await plansApi.patchPlans(plan.id, {
        method: 'PATCH',
        body: JSON.stringify({ moves: [{ order_id: Number(orderId), to_trip_id: null }] }),
      })
    },

    async defer(orderId, reason) {
      await deferralsApi.postDeferrals({
        method: 'POST',
        body: JSON.stringify({
          order_id: Number(orderId),
          reason_code: toBackendReason(reason),
          explanation: reason,
        }),
      })
    },

    async reviewAllocation() {
      const plans = await plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[])
      const plan = plans[0]
      if (plan) {
        try {
          localStorage.setItem(`waypoint.plan.reviewed.${plan.id}`, 'true')
        } catch {
          /* Device storage can be unavailable; preserve the current fallback. */
        }
        await plansApi.validatePlan(plan.id, { method: 'POST' }).catch(() => {})
      }
    },

    async publish() {
      const plans = await plansApi.getDraftPlans<ApiPlan[]>().catch(() => [] as ApiPlan[])
      const plan = plans[0]
      if (!plan) throw new Error('No draft plan to publish')
      await plansApi.publishPlan(plan.id, { method: 'POST' })
    },

    async release(loadId) {
      await loadingApi.releaseLoadingTrip(loadId, { method: 'POST' })
    },

    async closeIntake() {
      await ordersApi.postOrdersClose({ method: 'POST' })
    },
  }
}
