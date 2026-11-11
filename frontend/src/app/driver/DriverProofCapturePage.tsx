import { useDriverProofActions } from '@/queries/driver/useDriverProofActions'
import { DriverActions } from '@/components/molecules/driver/DriverActions'
import { useDriverStop } from '@/queries/driver/useDriverData'
import { DriverStopLayout } from '@/components/templates/driver/DriverStopLayout'
import { DriverLink } from '@/components/molecules/driver/DriverLink'
import { DriverPhotoPreview } from '@/components/molecules/driver/DriverPhotoPreview'
import { DriverPhotoPicker } from '@/components/molecules/driver/DriverPhotoPicker'

export default function DriverProofCapturePage() {
  const state = useDriverStop()
  const { capturePhoto, busy } = useDriverProofActions(state)
  return (
    <DriverStopLayout state={state} title="Proof of delivery" proofStep>
      <p>Photograph the delivered goods clearly before submitting the delivery.</p>
      <DriverPhotoPreview />
      <DriverPhotoPicker busy={busy} onPick={capturePhoto} />
      {state.draft && (
        <DriverLink to={state.href('/driver/proof/review')} variant="outline">
          Review saved photograph
        </DriverLink>
      )}
      <DriverActions>
        <DriverLink to={state.href('/driver/proof/camera-unavailable')} variant="secondary">
          Camera denied or unavailable
        </DriverLink>
        <DriverLink to={state.href('/driver/arrival')} variant="secondary">
          Cancel
        </DriverLink>
      </DriverActions>
      <p className="text-sm leading-relaxed text-muted-foreground">
        A photo is required before completion.
      </p>
    </DriverStopLayout>
  )
}
