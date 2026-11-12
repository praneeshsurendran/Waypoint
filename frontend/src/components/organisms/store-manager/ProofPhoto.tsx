import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/atoms/dialog'
import { BackIcon } from '@/components/atoms/shellIcons'
import { Action } from '@/components/atoms/store-manager/StoreControls'
import { formatShortDate } from '@/utils/calendar'
import { clock12 } from '@/utils/store-manager/timeText'
import type { Evidence } from '@/types/models'
import { ManagerSignOffDetails } from '@/components/organisms/ManagerSignOffDetails'
import fallback from '@/components/organisms/store-manager/assets/delivery-photo.png'

/** The delivery photograph, or the design's placeholder illustration before a photo is synced. */
export function ProofImage({ url, alt }: { url?: string | undefined; alt: string }) {
  return (
    <div className="sm-photo-frame">
      <img src={url ?? fallback} alt={alt} />
    </div>
  )
}

export function ProofDialog({
  open,
  onClose,
  orderId,
  outletId,
  url,
  capturedAt,
  evidence,
}: {
  open: boolean
  onClose: () => void
  orderId: string
  outletId: string
  url?: string | undefined
  capturedAt?: string | undefined
  evidence?: Evidence | undefined
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="sm-dialog max-h-[calc(100dvh-32px)] overflow-y-auto !gap-4 !rounded-2xl !p-5 sm:!max-w-[380px]"
      >
        <div className="breadcrumbs !mb-0" aria-hidden="true">
          <button type="button" className="breadcrumb-back" onClick={onClose} tabIndex={-1}>
            <BackIcon />
            Back
          </button>
          <span className="breadcrumb-divider" />
          <ol>
            <li>
              <span>Order</span>
            </li>
            <li>
              <span>/</span>
              <span aria-current="page">Proof</span>
            </li>
          </ol>
        </div>
        <DialogTitle className="!text-[22px] !font-semibold">Delivery photograph</DialogTitle>
        <DialogDescription className="sr-only">
          The photograph the driver took when delivering {orderId}.
        </DialogDescription>
        <ProofImage url={url} alt={`Delivery photograph for ${orderId}`} />
        <p className="sm-photo-caption">
          {orderId} · {outletId}
          <br />
          {capturedAt
            ? `Captured by driver · ${formatShortDate(capturedAt)}, ${clock12(capturedAt)}`
            : 'Captured by driver'}
        </p>
        {evidence?.kind === 'delivery' && (
          <ManagerSignOffDetails signature={evidence.signature} signOff={evidence.managerSignOff} />
        )}
        <Action variant="grey" onClick={onClose}>
          Close
        </Action>
      </DialogContent>
    </Dialog>
  )
}
