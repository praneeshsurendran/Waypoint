import type { ManagerSignOff } from '@/types/deliveryVerification'

export type ConnectivityStatus = 'online' | 'offline' | 'syncing'

export type ProofStatus = 'none' | 'captured' | 'localPending' | 'uploading' | 'accepted' | 'failed'

export type DeliveryStatus =
  'enRoute' | 'parked' | 'proofRequired' | 'pendingSync' | 'delivered' | 'issueReported'

/** A durable draft is a local photograph, never an upload acknowledgement. */
export interface DriverProofDraft {
  stopId: string
  photo: Blob
  fileName: string
  stage: 'captured' | 'attached'
  quantity: number
  receiver: string
  acknowledged: boolean
  exception: string
  revision: number
  createdAt: string
  signature?: Blob
  managerSignOff?: ManagerSignOff
  photoDigest?: string
}
