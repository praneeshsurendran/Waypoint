import * as adminApi from '@/api/endpoints/admin'
import * as referenceApi from '@/api/endpoints/reference'
import { invalidateOutletReferences } from '@/infrastructure/adapters/http/reference'
import type { OutletsApi } from '@/types/api/outlets'
import { profileFromReference } from '@/utils/outlets'

export function createHttpOutletsApi(): OutletsApi {
  return {
    async listOutlets() {
      const outlets = await referenceApi.getReferenceOutlets()
      return outlets.map(profileFromReference).sort((a, b) => a.id.localeCompare(b.id))
    },
    async createOutlet(input) {
      const created = await adminApi.postAdminOutlets({
        method: 'POST',
        body: {
          name: input.name,
          brand: input.brand,
          district: input.district,
          depot_code: input.depot,
          parking_constraint: input.parking === 'van_only' ? 'van_only' : null,
          window_open_time: `${input.earliest}:00`,
          window_close_time: `${input.latest}:00`,
        },
      })
      invalidateOutletReferences()
      return profileFromReference(created)
    },
  }
}
