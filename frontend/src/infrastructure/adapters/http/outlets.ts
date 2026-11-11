import * as referenceApi from '@/api/endpoints/reference'
import * as adminApi from '@/api/endpoints/admin'
import type { OutletsApi } from '@/types/api/outlets'
import type { ApiOutlet } from '@/types/api/reference'
import { profileFromReference } from '@/utils/outlets'
import { invalidateOutletReferences } from '@/infrastructure/adapters/http/reference'

export function createHttpOutletsApi(): OutletsApi {
  return {
    async listOutlets() {
      const outlets = await referenceApi.getReferenceOutlets<ApiOutlet[]>()
      return outlets.map(profileFromReference).sort((a, b) => a.id.localeCompare(b.id))
    },
    async createOutlet(input) {
      const created = await adminApi.postAdminOutlets<ApiOutlet>({
        method: 'POST',
        body: JSON.stringify({
          name: input.name,
          brand: input.brand,
          district: input.district,
          depot_code: input.depot,
          parking_constraint: input.parking === 'van_only' ? 'van_only' : null,
          window_open_time: `${input.earliest}:00`,
          window_close_time: `${input.latest}:00`,
        }),
      })
      invalidateOutletReferences()
      return profileFromReference(created)
    },
  }
}
