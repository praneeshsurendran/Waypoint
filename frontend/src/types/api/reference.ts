import type { components as Identity } from '@/types/generated/identity'
import type { components as Network } from '@/types/generated/network'

export type ApiUserProfile = Identity['schemas']['UserProfile']
export type LoginResponse = Identity['schemas']['TokenResponse']
export type ApiOutlet = Network['schemas']['OutletOut']
