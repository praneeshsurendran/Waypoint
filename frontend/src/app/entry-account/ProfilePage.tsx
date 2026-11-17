import '@/design-system/features/store.css'
import '@/design-system/features/profile.css'
import { useState } from 'react'
import { toast } from 'sonner'
import { roleModules } from '@/constants/roleWorkspaces'
import { useOwnContact } from '@/hooks/useOwnContact'
import { useStoreProfile } from '@/queries/store-manager/useStore'
import { useStoreAction } from '@/queries/store-manager/useStoreAction'
import { useApis } from '@/app/providers/ApisContext'
import { StorePage } from '@/components/templates/store-manager/StorePage'
import { FieldInput } from '@/components/molecules/store-manager/StoreFields'
import { Action } from '@/components/atoms/store-manager/StoreControls'

export default function ProfilePage() {
  const own = useOwnContact()
  if (!own.loaded) return <p>Loading profile…</p>
  return (
    <ProfileEditor
      key={own.session.memberId ?? own.session.role}
      initial={own.contact}
      session={own.session}
    />
  )
}

function ProfileEditor({
  initial,
  session,
}: {
  initial: { name: string; mobile: string; email: string }
  session: ReturnType<typeof useOwnContact>['session']
}) {
  const action = useStoreAction()
  const apis = useApis()
  const outlet = useStoreProfile()
  const [saved, setSaved] = useState(initial)
  const [draft, setDraft] = useState(initial)
  const [attempted, setAttempted] = useState(false)
  const [request, setRequest] = useState('')
  const [requestError, setRequestError] = useState('')
  const role = roleModules.find((module) => module.key === session.role)?.label ?? 'User'
  const dirty = JSON.stringify(saved) !== JSON.stringify(draft)
  const errors = {
    name: draft.name.trim().length < 2 ? 'Enter your full name.' : undefined,
    mobile:
      draft.mobile.trim() !== '' && draft.mobile.replace(/\D/g, '').length < 7
        ? 'Enter a phone number with at least 7 digits.'
        : undefined,
    email:
      draft.email.trim() !== '' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.email)
        ? 'Enter a valid email address.'
        : undefined,
  }
  const save = () => {
    setAttempted(true)
    if (Object.values(errors).some(Boolean) || !session.memberId) return
    action.send(
      { kind: 'profile', memberId: session.memberId, ...draft },
      'Contact details saved',
      () => {
        setSaved(draft)
        setAttempted(false)
        toast.success('Contact details saved')
      },
    )
  }
  const sendRequest = () => {
    if (request.trim().length < 4) {
      setRequestError('Describe what should change.')
      return
    }
    if (!session.memberId) return
    action.runThen(
      () => apis.team.requestAccountChange(session.memberId ?? '', request.trim()),
      () => {
        setRequest('')
        setRequestError('')
        toast.success('Request sent to your administrator')
      },
    )
  }
  return (
    <StorePage>
      <header className="sm-intro">
        <h1>Profile</h1>
        <p>
          {session.outletId ?? session.vehicleId} · {role}
        </p>
      </header>
      <section className="sm-panel" aria-label="Your details">
        <h2 className="sm-h22">Your details</h2>
        <FieldInput
          label="Full name"
          value={draft.name}
          error={attempted ? errors.name : undefined}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
        />
        <FieldInput
          label="Phone"
          value={draft.mobile}
          error={attempted ? errors.mobile : undefined}
          onChange={(event) => setDraft({ ...draft, mobile: event.target.value })}
        />
        <FieldInput
          label="Email"
          value={draft.email}
          error={attempted ? errors.email : undefined}
          onChange={(event) => setDraft({ ...draft, email: event.target.value })}
        />
        <div className="sm-actions">
          <Action onClick={save} disabled={!dirty || action.isPending}>
            Save changes
          </Action>
          <Action
            variant="outline"
            onClick={() => {
              setDraft(saved)
              setAttempted(false)
            }}
            disabled={!dirty}
          >
            Discard changes
          </Action>
        </div>
      </section>
      <section className="sm-panel" aria-label="Assignment">
        <h2 className="sm-h22">Assignment</h2>
        <p>
          {role} · {session.outletId ?? session.vehicleId ?? session.depot}
        </p>
        {session.role === 'store-manager' && outlet.profile?.brand === 'Fresh' && (
          <p>Fresh goods must arrive before the store opens at 8:00 AM</p>
        )}
        {session.role === 'store-manager' && outlet.profile && (
          <p>
            Waypoint {outlet.profile.brand}
            {outlet.profile.mall ? ' · The mall only accepts deliveries in its access window.' : ''}
          </p>
        )}
        <p>Your administrator sets your role and assignment. Request a change below.</p>
        <FieldInput
          label="What should change?"
          value={request}
          error={requestError || undefined}
          onChange={(event) => setRequest(event.target.value)}
        />
        <Action onClick={sendRequest} disabled={action.isPending}>
          Send request
        </Action>
      </section>
    </StorePage>
  )
}
