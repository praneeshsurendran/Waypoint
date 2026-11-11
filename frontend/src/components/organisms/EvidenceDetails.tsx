import { useEvidence } from '@/queries/useOperations'
import { Notice } from '@/components/molecules/Common'
import { formatTime } from '@/utils/formatTime'
import { ManagerSignOffDetails } from '@/components/organisms/ManagerSignOffDetails'

export function EvidenceDetails({ evidenceId }: { evidenceId: string }) {
  const { evidence, url } = useEvidence(evidenceId)
  return evidence ? (
    <div className="space-y-4">
      {url && <img src={url} alt="Retained evidence photograph" className="proof-image" />}
      <p className="text-sm">
        {evidence.kind === 'attempt'
          ? 'Unsuccessful attempt · delivery remains incomplete'
          : `${evidence.quantity} cases · Receiver: ${evidence.receiver || 'Exception recorded'}`}
      </p>
      {evidence.receiverException && (
        <Notice title="Recorded exception">{evidence.receiverException}</Notice>
      )}
      {evidence.kind === 'delivery' && (
        <ManagerSignOffDetails signature={evidence.signature} signOff={evidence.managerSignOff} />
      )}
      <p className="text-xs text-muted-foreground">
        Original revision {evidence.revision} · {evidence.fileName} ·{' '}
        {formatTime(evidence.createdAt)}
      </p>
    </div>
  ) : (
    <p className="text-sm text-muted-foreground">Loading saved evidence…</p>
  )
}
