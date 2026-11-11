import type { Evidence, QueuedAction, Stop, Order } from '@/types/models'

import type { DriverProofDraft, ProofStatus, DeliveryStatus } from '@/types/driverProof'

import { managerSignOffErrors, signedManifestMatches } from '@/utils/deliveryVerification'

export function proofStatus(
  evidence?: Evidence,
  record?: QueuedAction,
  draft?: DriverProofDraft,
  manifest?: { stop: Stop; orders: Order[] },
): ProofStatus {
  if (
    evidence?.kind === 'delivery' &&
    evidence.accepted &&
    !managerSignOffErrors(
      {
        stopId: evidence.entityId,
        quantity: evidence.quantity ?? NaN,
        receiver: evidence.receiver ?? '',
        exception: evidence.receiverException ?? '',
        fileName: evidence.fileName,
        revision: evidence.revision,
      },
      evidence.signature,
      evidence.managerSignOff,
    ).length &&
    (!manifest || signedManifestMatches(manifest.stop, manifest.orders, evidence.managerSignOff)) &&
    record?.status === 'accepted' &&
    record.evidenceId === evidence.id
  )
    return 'accepted'
  if (record?.status === 'syncing') return 'uploading'
  if (record?.status === 'retry') return 'failed'
  if (record || evidence) return 'localPending'
  return draft ? 'captured' : 'none'
}

export function deliveryStatus(stop: Stop, proof: ProofStatus): DeliveryStatus {
  // Even malformed/stale stop data cannot show Delivered without accepted proof.
  if (stop.status === 'Delivered' && proof === 'accepted') return 'delivered'
  if (stop.status === 'Cannot deliver') return 'issueReported'
  if (stop.status === 'Proof pending' || stop.status === 'Delivered') return 'pendingSync'
  if (stop.status === 'Arrived') return proof === 'none' ? 'parked' : 'proofRequired'
  return 'enRoute'
}

export function handoffErrors(draft: DriverProofDraft, expected: number): string[] {
  const errors: string[] = []
  if (!draft.photo.size) errors.push('A delivery photograph is required.')
  if (!Number.isInteger(draft.quantity) || draft.quantity < 0 || draft.quantity > expected)
    errors.push('Enter a whole case count between zero and the expected quantity.')
  if (draft.quantity !== expected && draft.exception.trim().length < 4)
    errors.push('Explain the quantity difference.')
  if (!draft.acknowledged) errors.push('The Store Manager must confirm unloading and receipt.')
  errors.push(...managerSignOffErrors(draft, draft.signature, draft.managerSignOff))
  return errors
}

export function attachPhoto(draft: DriverProofDraft): DriverProofDraft {
  if (!draft.photo.size) throw new Error('Capture a photograph before attaching proof.')
  return { ...draft, stage: 'attached' }
}
