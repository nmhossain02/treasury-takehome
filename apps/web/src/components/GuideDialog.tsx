import { useEffect, useRef } from 'react'

interface GuideDialogProps {
  onClose: () => void
}

const steps = [
  {
    icon: '↑',
    title: 'Upload images',
    description: 'Add one or more clear photos of the label. Include front and back views when available.',
  },
  {
    icon: '⌕',
    title: 'Label Lens finds a matching COLA',
    description: 'The app reads the label, finds likely public records, and shows its comparison.',
  },
  {
    icon: '✓ / ×',
    title: 'Choose mock approve or deny',
    description: 'Record a simulated COLAs Online decision. Nothing is sent to a government system.',
  },
]

export function GuideDialog({ onClose }: GuideDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>('button, [tabindex]:not([tabindex="-1"])'),
      )
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (!first || !last) return
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="dialog-backdrop guide-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose()
    }}>
      <div
        ref={dialogRef}
        className="guide-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-heading"
        aria-describedby="guide-description"
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Quick guide</p>
            <h2 id="guide-heading" ref={headingRef} tabIndex={-1}>How Label Lens works</h2>
          </div>
          <button className="close-button" type="button" onClick={onClose} aria-label="Close guide">×</button>
        </div>
        <p id="guide-description" className="guide-intro">
          Verify an alcohol label in three steps.
        </p>
        <ol className="guide-steps">
          {steps.map((step, index) => (
            <li key={step.title}>
              <span className="guide-step-icon" aria-hidden="true">{step.icon}</span>
              <div>
                <small>Step {index + 1}</small>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="guide-disclaimer">
          <strong>Prototype only:</strong> public COLA metadata is read-only and mock decisions stay local.
        </p>
        <div className="guide-actions">
          <button className="button button-primary" type="button" onClick={onClose}>Got it</button>
        </div>
      </div>
    </div>
  )
}
