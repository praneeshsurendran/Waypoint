import { Link } from 'react-router-dom'
import { fieldRoles } from '@/constants/entryRoles'
import { roleTitle } from '@/utils/roleTitle'
import '@/design-system/features/entry.css'

export function EntryFooter() {
  return (
    <footer className="entry-footer">
      <div className="entry-footer-top">
        <div>
          <Link to="/welcome" className="entry-footer-brand">
            waypoint
          </Link>
          <p>Every delivery. A clearer day.</p>
        </div>
        <div className="entry-footer-columns">
          <div>
            <h2>Product</h2>
            {fieldRoles.map((role) => (
              <Link key={role.key} to={role.home}>
                {roleTitle(role.label)}
              </Link>
            ))}
          </div>
          <div>
            <h2>Company</h2>
            <span>About Waypoint</span>
            <span>Careers</span>
            <span>Contact</span>
          </div>
          <div>
            <h2>Support</h2>
            <span>Help center</span>
            <span>Status</span>
            <span>support@waypointgroup.lk</span>
          </div>
        </div>
      </div>
      <div className="entry-footer-bottom">
        <p>
          © 2026 Waypoint Group <span>Privacy</span> <span>Terms</span>
        </p>
        <span className="entry-status">
          <span aria-hidden="true" />
          All systems normal
        </span>
      </div>
    </footer>
  )
}
