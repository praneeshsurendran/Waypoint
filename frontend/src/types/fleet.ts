import type { Brand } from '@/types/outlets'
import type { Vehicle } from '@/types/models'

/** What an administrator enters to add a vehicle; the system assigns the id (VEH061 and so on). */
export interface NewVehicle {
  brand: Brand
  type: Vehicle['type']
  /** Only Fresh carries chilled goods, so only Fresh vehicles can be refrigerated. */
  reefer: boolean
  depot: string
  weightCapacity: number
  volumeCapacity: number
  /** Number plate, optional. */
  registration?: string
}
