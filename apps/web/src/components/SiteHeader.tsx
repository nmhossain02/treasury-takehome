import { useRef, useState } from 'react'
import type { Readiness } from '../hooks/useVerificationWorkflow'
import { GuideDialog } from './GuideDialog'

interface SiteHeaderProps {
  readiness: Readiness
  onRetry: () => Promise<void>
}

const readinessLabels: Record<Readiness, string> = {
  preparing: 'Preparing verifier',
  ready: 'Verifier ready',
  unavailable: 'Readiness unconfirmed',
}

export function SiteHeader({ readiness, onRetry }: SiteHeaderProps) {
  const [guideOpen, setGuideOpen] = useState(false)
  const guideTriggerRef = useRef<HTMLButtonElement>(null)

  const closeGuide = () => {
    setGuideOpen(false)
    window.setTimeout(() => guideTriggerRef.current?.focus(), 0)
  }

  return (
    <>
      <header className="site-header">
        <a className="skip-link" href="#main-content">Skip to main content</a>
        <div className="header-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden="true">LL</span>
            <div><strong>Label Lens</strong><span>Alcohol label review</span></div>
          </div>
          <div className="header-actions">
            <button
              ref={guideTriggerRef}
              className="info-button"
              type="button"
              aria-label="How to use Label Lens"
              aria-haspopup="dialog"
              aria-expanded={guideOpen}
              onClick={() => setGuideOpen(true)}
              title="How to use Label Lens"
            >
              <span aria-hidden="true">i</span>
            </button>
            <div className={`readiness readiness-${readiness}`} role="status" aria-live="polite">
              <span aria-hidden="true" />
              {readinessLabels[readiness]}
              {readiness === 'unavailable' ? (
                <button type="button" onClick={() => void onRetry()}>Retry</button>
              ) : null}
            </div>
          </div>
        </div>
      </header>
      {guideOpen ? <GuideDialog onClose={closeGuide} /> : null}
    </>
  )
}
