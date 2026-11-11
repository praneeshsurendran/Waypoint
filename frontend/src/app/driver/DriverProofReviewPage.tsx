import { useDriverProofActions } from '@/queries/driver/useDriverProofActions'
import { DriverActions } from '@/components/molecules/driver/DriverActions'
import { useDriverStop } from '@/queries/driver/useDriverData'
import { DriverStopLayout } from '@/components/templates/driver/DriverStopLayout'
import { DriverPhotoPreview } from '@/components/molecules/driver/DriverPhotoPreview'
import { DriverLink } from '@/components/molecules/driver/DriverLink'
import { DriverButton as Button } from '@/components/atoms/driver/DriverButton'
import { StatusBadge } from '@/components/molecules/Common'

export default function DriverProofReviewPage() {
  const state = useDriverStop()
  const { attachProof, busy } = useDriverProofActions(state)
  return (
    <DriverStopLayout state={state} title="Is everything clearly visible?" proofStep requireDraft>
      <DriverPhotoPreview photo={state.draft?.photo} fileName={state.draft?.fileName} />
      <StatusBadge tone="neutral">Captured · saved locally · not submitted</StatusBadge>
      <DriverActions>
        <Button onClick={attachProof} disabled={busy}>
          Use this photo
        </Button>
        <DriverLink to={state.href('/driver/proof/capture')} variant="secondary">
          Retake photo
        </DriverLink>
      </DriverActions>
      <p className="text-sm leading-relaxed text-muted-foreground">
        Your existing photo remains saved until a replacement is captured.
      </p>
    </DriverStopLayout>
  )
}
