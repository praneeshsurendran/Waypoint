import * as ordersApi from '@/api/endpoints/orders'
import * as referenceApi from '@/api/endpoints/reference'
import type { OrdersApi, ReceiptIssue } from '@/types/api/orders'
import type { ApiOrder } from '@/types/api/responses'
import { mapOrder } from '@/mappers/operations'

import type { OutletProfile } from '@/types/outlets'
import { profileFromReference } from '@/utils/outlets'
import type { ApiOutlet } from '@/types/api/reference'

export async function deliveryDay(): Promise<{
  date?: string
  next?: string
  published?: boolean
}> {
  type Intake = { delivery_date?: string; next_delivery_date?: string; published?: boolean }
  const intake = await ordersApi.getOrdersIntakeStatus<Intake>().catch(() => ({}) as Intake)
  return {
    date: intake.delivery_date,
    next: intake.next_delivery_date ?? intake.delivery_date,
    published: intake.published,
  }
}

export function createHttpOrdersApi(outletId?: string): OrdersApi {
  return {
    async listOrders(filter = {}) {
      const params = new URLSearchParams()
      const scope = filter.outletId ?? outletId
      if (scope) params.set('outlet_id', scope)
      if (filter.status) params.set('status', filter.status.toUpperCase())
      if (filter.date) params.set('date', filter.date)
      const [orders, intake] = await Promise.all([
        ordersApi.getOrders<ApiOrder[]>(params),
        filter.outletId ? deliveryDay() : Promise.resolve(undefined),
      ])
      // For one outlet this is the next delivery; its earlier orders come from listHistory.
      const day = filter.day === 'next' ? intake?.next : intake?.date
      return orders
        .filter((o) => !day || o.delivery_date === day)
        .map((o) => {
          const order = mapOrder(o, intake?.published)
          // A store learns its vehicle, or that it was deferred, once the plan is published; before that
          // the plan is only the dispatcher's draft and can still change.
          if (
            filter.outletId &&
            !intake?.published &&
            (order.status === 'Allocated' || order.status === 'Deferred')
          )
            return {
              ...order,
              status: 'Confirmed' as const,
              vehicleId: undefined,
              trip: undefined,
              deferralReason: undefined,
            }
          return order
        })
    },

    async listDrafts() {
      return [] // drafts are device-local; backend has no draft concept
    },

    async getIntakeStatus() {
      const data = await ordersApi
        .getOrdersIntakeStatus<{
          cutoff_closed: boolean
          published: boolean
          now?: string
          delivery_date?: string
          next_delivery_date?: string
        }>()
        .catch(() => ({
          cutoff_closed: false,
          published: true,
          now: undefined,
          delivery_date: undefined,
          next_delivery_date: undefined,
        }))
      return {
        cutoffClosed: data.cutoff_closed,
        published: data.published,
        now: data.now,
        deliveryDate: data.delivery_date,
        nextDeliveryDate: data.next_delivery_date,
      }
    },

    async closeIntake() {
      await ordersApi.postOrdersClose({ method: 'POST' })
    },

    async createOrder(outlet, temperature, cases, window) {
      await ordersApi.postOrders({
        method: 'POST',
        body: JSON.stringify({
          outlet_id: outlet,
          temperature_class: temperature === 'Chilled' ? 'CHILLED' : 'AMBIENT',
          cases,
          window_open: window,
        }),
      })
    },

    async placeOrders(outlet, inputs) {
      // An outlet has one dry and one chilled order per delivery day, so a type it already has is edited.
      const [intake, mine] = await Promise.all([
        deliveryDay(),
        ordersApi.listOrders<ApiOrder[]>().catch(() => [] as ApiOrder[]),
      ])
      const today = (order: ApiOrder) =>
        order.outlet_id === outlet &&
        order.status !== 'CANCELLED' &&
        (!intake.next || order.delivery_date === intake.next)
      // Fresh has one order per temperature; Style has one a day. Tech orders as needed, so it adds.
      const existingFor = (temperature: string) =>
        mine.find(
          (order) =>
            today(order) &&
            ((order.brand === 'Fresh' && order.temperature_class === temperature) ||
              order.brand === 'Style'),
        )
      for (const input of inputs) {
        const inp = {
          ...input,
          orderId:
            input.orderId ??
            (outlet && input.temperature
              ? existingFor(input.temperature === 'Chilled' ? 'CHILLED' : 'AMBIENT')?.id?.toString()
              : undefined),
        }
        if (inp.orderId) {
          await ordersApi.patchOrders(inp.orderId, {
            method: 'PATCH',
            body: JSON.stringify({
              total_cases: inp.cases,
              // Only a Tech store states a weight; for everyone else the server works it out.
              ...(inp.weightEntered ? { total_weight: inp.weight } : {}),
            }),
          })
        } else {
          await ordersApi.postOrders({
            method: 'POST',
            body: JSON.stringify({
              outlet_id: outlet,
              temperature_class: inp.temperature === 'Chilled' ? 'CHILLED' : 'AMBIENT',
              total_cases: inp.cases,
              // Only a Tech store states a weight; for everyone else the server works it out.
              ...(inp.weightEntered ? { total_weight: inp.weight } : {}),
            }),
          })
        }
      }
    },

    async editOrder(orderId, cases) {
      await ordersApi.patchOrders(orderId, {
        method: 'PATCH',
        body: JSON.stringify({ cases }),
      })
    },

    saveDraft: async () => {}, // device-only
    saveDrafts: async () => {}, // device-only

    async confirmReceipt(orderId) {
      await ordersApi.confirmOrderReceipt(orderId, {
        method: 'POST',
        body: JSON.stringify({ outcome: 'FULL' }),
      })
    },

    async reportReceiptIssue(orderId, issue: ReceiptIssue) {
      await ordersApi.confirmOrderReceipt(orderId, {
        method: 'POST',
        body: JSON.stringify({
          outcome: issue.kind === 'Missing' ? 'SHORT' : 'DAMAGED',
          received_qty: issue.received,
          affected_qty: issue.affected,
          notes: issue.description,
        }),
      })
    },

    async acknowledgeDeferral(orderId) {
      // Record acknowledgement as a note
      await ordersApi.reportOrderIssue(orderId, {
        method: 'POST',
        body: JSON.stringify({
          type: 'OTHER',
          description: 'Deferral acknowledged by store manager.',
        }),
      })
    },

    async listHistory(filter = {}) {
      const params = new URLSearchParams()
      const scope = filter.outletId ?? outletId
      if (scope) params.set('outlet_id', scope)
      const [orders, intake] = await Promise.all([
        ordersApi.getOrders<ApiOrder[]>(params.toString()).catch(() => [] as ApiOrder[]),
        deliveryDay(),
      ])
      return orders
        .filter((o) => !intake.date || o.delivery_date !== intake.date)
        .map((o) => mapOrder(o))
        .sort((a, b) => (b.placedAt ?? '').localeCompare(a.placedAt ?? ''))
    },

    async getOutletProfile(id: string): Promise<OutletProfile> {
      return profileFromReference(await referenceApi.getReferenceOutlet<ApiOutlet>(id))
    },

    async cancelOrder(orderId) {
      await ordersApi.cancelOrder(orderId, { method: 'POST' })
    },
  }
}
