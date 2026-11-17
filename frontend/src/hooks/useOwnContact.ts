import { useOperations } from '@/queries/useOperations'
import { useSession } from '@/hooks/useSession'
import { getUser } from '@/infrastructure/storage/authSession'
import { useOutbox } from '@/queries/store-manager/useOutbox'

export function useOwnContact() {
  const session = useSession()
  const snapshot = useOperations()
  const stored = getUser()
  const member = snapshot.data?.members.find((candidate) => candidate.id === session.memberId)
  const changes = useOutbox(session.outletId ?? '')
  const pending = changes
    .filter((item) => item.request.kind === 'profile' && item.request.memberId === session.memberId)
    .at(-1)?.request
  return {
    session,
    loaded: Boolean(stored || snapshot.data),
    contact:
      pending?.kind === 'profile'
        ? { name: pending.name, mobile: pending.mobile, email: pending.email }
        : {
            name: stored?.full_name ?? member?.name ?? session.name,
            mobile: stored?.phone ?? member?.mobile ?? '',
            email: stored?.email ?? member?.email ?? '',
          },
  }
}
