import { useNavigate, Link } from 'react-router-dom'
import { getUser } from '@/infrastructure/auth'
import { ROLE_HOME_MAP } from '@/app/router/guards/RoleRouteGuard'
import { Button } from '@/components/atoms/button'

export function NotFoundView() {
  const navigate = useNavigate()
  const user = getUser()
  const roleUpper = (user?.role || '').toUpperCase()
  const homePath = user ? (ROLE_HOME_MAP[roleUpper] ?? '/workspaces') : '/welcome'

  return (
    <div className="empty-state">
      <h1>Page not found</h1>
      <p>The screen or address you requested does not exist.</p>
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1rem' }}>
        <Button variant="outline" onClick={() => navigate(-1)}>
          Go back
        </Button>
        <Link to={homePath}>
          <Button>{user ? 'Go to your workspace' : 'Back to home'}</Button>
        </Link>
      </div>
    </div>
  )
}
