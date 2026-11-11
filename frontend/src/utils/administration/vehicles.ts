import type { Vehicle, TeamMember } from '@/types/models'

export const driverOf = (vehicle: Pick<Vehicle, 'id'>, members: TeamMember[]) =>
  members.find((member) => member.role === 'driver' && member.vehicleId === vehicle.id)

export const vehicleStatusTone = (status: Vehicle['status']) =>
  status === 'Available'
    ? 'green'
    : status === 'Offline'
      ? 'red'
      : status === 'Loading'
        ? 'amber'
        : 'orange'

export const capacityText = (vehicle: Pick<Vehicle, 'weightCapacity' | 'volumeCapacity'>) =>
  `${vehicle.weightCapacity.toLocaleString('en-GB')} kg · ${vehicle.volumeCapacity} m³`

export const vehicleTypes: {
  type: Vehicle['type']
  reefer: boolean
  label: string
  note: string
}[] = [
  {
    type: 'Truck',
    reefer: false,
    label: 'Dry-box truck',
    note: 'Garments, appliances and dry groceries.',
  },
  {
    type: 'Truck',
    reefer: true,
    label: 'Refrigerated truck',
    note: 'Chilled and frozen groceries. Fresh only.',
  },
  {
    type: 'Van',
    reefer: false,
    label: 'Van',
    note: 'Small loads and outlets trucks cannot reach.',
  },
  {
    type: 'Van',
    reefer: true,
    label: 'Refrigerated van',
    note: 'Small chilled loads. Fresh only.',
  },
]
