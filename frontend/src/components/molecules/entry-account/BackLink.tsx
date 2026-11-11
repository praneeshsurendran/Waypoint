import { useNavigate, Link } from 'react-router-dom'
import { ChevronLeft } from 'lucide-react'

import '@/design-system/features/entry.css'

export function BackLink({ trail }: { trail: string[] }) {
  const navigate = useNavigate()
  return (
    <nav className="entry-back" aria-label="Breadcrumb">
      <button
        type="button"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/welcome'))}
      >
        <ChevronLeft size={16} />
        Back
      </button>
      <span className="entry-back-divider" aria-hidden="true" />
      <Link to="/welcome">Home</Link>
      {trail.map((item) => (
        <span key={item} className="entry-back-current">
          / {item}
        </span>
      ))}
    </nav>
  )
}
