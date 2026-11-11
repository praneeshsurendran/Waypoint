import { Check, Minus } from 'lucide-react'
import type { Workspace } from '@/types/models'
import { AdminIntro } from '@/components/molecules/administration/AdminFields'
import { AdminPage } from '@/components/templates/administration/AdminPage'
import { capabilities, roleLabels } from '@/utils/administration/team'

const columns: Workspace[] = ['dispatcher', 'loader', 'driver', 'store-manager', 'administration']

/** Roles & access: what each role can do, so access is a decision and not a guess. */
export default function RolesPage() {
  return (
    <AdminPage>
      <AdminIntro
        kicker="Administration · Access"
        title="Roles & access"
        lead="Each role sees only what it needs. Administrators manage people, not deliveries."
      />
      <div className="ad-table-card ad-matrix-wrap">
        <table className="ad-table ad-matrix">
          <thead>
            <tr>
              <th>Capability</th>
              {columns.map((role) => (
                <th key={role}>{roleLabels[role]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {capabilities.map((capability) => (
              <tr key={capability.label}>
                <td>{capability.label}</td>
                {columns.map((role) => {
                  const value = capability.access[role]
                  return (
                    <td key={role}>
                      {value === true ? (
                        <Check size={18} aria-label="Yes" />
                      ) : value ? (
                        <small>{value}</small>
                      ) : (
                        <Minus size={18} className="ad-dash" aria-label="No" />
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div className="ad-table-foot">
          <span>
            The Administrator cannot allocate, load or deliver. Operational decisions stay with the
            people who own them.
          </span>
          <span>
            {columns.length} roles · {capabilities.length} capabilities
          </span>
        </div>
      </div>
    </AdminPage>
  )
}
