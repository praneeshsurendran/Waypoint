import type { Brand, Parking, OutletProfile } from '@/types/outlets'

import type { TeamMember } from '@/types/models'

export const brands: { brand: Brand; summary: string }[] = [
  { brand: 'Fresh', summary: 'Groceries, chilled and frozen. Daily, before the store opens.' },
  { brand: 'Style', summary: 'Hanging garments and cartons. Weekly, with seasonal peaks.' },
  { brand: 'Tech', summary: 'Appliances and electronics. As needed, fragile and valuable.' },
]

export const parkingOptions: { value: Parking; label: string; detail: string }[] = [
  {
    value: 'normal',
    label: 'Any vehicle',
    detail: 'Trucks and vans can reach the delivery point.',
  },
  { value: 'van_only', label: 'Vans only', detail: 'Trucks cannot reach it; only small vans can.' },
  {
    value: 'mall_dock',
    label: 'Mall delivery window',
    detail: 'A shared mall dock that only accepts deliveries in a fixed window.',
  },
]

export const parkingLabel = (outlet: OutletProfile) =>
  parkingOptions.find(
    (option) => option.value === (outlet.parking ?? (outlet.mall ? 'mall_dock' : 'normal')),
  )?.label ?? 'Any vehicle'

export function time12(time: string) {
  const [h, m] = time.split(':').map(Number)
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`
}

export const windowLabel = (outlet: OutletProfile) =>
  `${time12(outlet.receiving.earliest)} – ${time12(outlet.receiving.latest)}`

export const timeOptions = Array.from({ length: 37 }, (_, index) => {
  const minutes = 4 * 60 + index * 30
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
})

export const minutesOf = (time: string) => Number(time.slice(0, 2)) * 60 + Number(time.slice(3))

export const managerOf = (outlet: { id: string }, members: TeamMember[]) =>
  members.find((member) => member.role === 'store-manager' && member.outletId === outlet.id)

export const outletAssignment = (outlet: OutletProfile) => `${outlet.id} · ${outlet.brand}`
