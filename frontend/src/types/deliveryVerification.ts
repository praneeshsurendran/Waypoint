/** Manager sign-off is bound to the reviewed handoff, not reusable on edited details. */
export type SignaturePoint = { x: number; y: number }

export type SignatureStroke = SignaturePoint[]

export interface ReceivedOrder {
  orderId: string
  expected: number
  received: number
}

export interface ManagerSignOff {
  method: 'signature'
  managerName: string
  remarks: string
  unloaded: boolean
  orders: ReceivedOrder[]
  strokes: SignatureStroke[]
  signedAt: string
  photoDigest: string
  binding: string
}

export interface SignedHandoff {
  stopId: string
  quantity: number
  receiver: string
  exception: string
  fileName: string
  revision: number
}
