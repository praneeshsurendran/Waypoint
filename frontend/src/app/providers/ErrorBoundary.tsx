import { Component } from 'react'
import type { ReactNode, ErrorInfo } from 'react'

import { Button } from '@/components/atoms/button'

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: boolean }> {
  state = { error: false }
  static getDerivedStateFromError() {
    return { error: true }
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(error, info)
  }
  render() {
    return this.state.error ? (
      <div className="empty-state">
        <h1>We couldn’t open this screen.</h1>
        <p>Your saved evidence remains in browser storage.</p>
        <Button onClick={() => window.location.reload()}>Reload workspace</Button>
      </div>
    ) : (
      this.props.children
    )
  }
}
