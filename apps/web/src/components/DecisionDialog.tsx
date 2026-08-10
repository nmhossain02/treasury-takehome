import { useEffect, useMemo, useRef, useState } from 'react'
import type { DecisionRequest, VerificationResponse } from '../types'

interface DecisionDialogProps {
  action: 'approve' | 'deny'
  verification: VerificationResponse
  busy: boolean
  error?: string
  onClose: () => void
  onSubmit: (decision: DecisionRequest) => void
}

function humanize(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function DecisionDialog({
  action,
  verification,
  busy,
  error,
  onClose,
  onSubmit,
}: DecisionDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const headingRef = useRef<HTMLHeadingElement>(null)
  const application = verification.application!
  const suggestedReasons = useMemo(
    () => (verification.checks ?? []).filter((check) => check.status !== 'pass'),
    [verification.checks],
  )
  const [reasonCodes, setReasonCodes] = useState(() => suggestedReasons.map((check) => check.id))
  const [disposition, setDisposition] = useState<'needs_correction' | 'rejected'>('needs_correction')
  const [notes, setNotes] = useState('')
  const [override, setOverride] = useState('')
  const [confirmReject, setConfirmReject] = useState(false)
  const [validation, setValidation] = useState<string[]>([])

  const conflicts = action === 'approve'
    ? verification.overall_status !== 'pass'
    : (verification.checks ?? []).every((check) => check.status === 'pass')
  const canReject = verification.allowed_dispositions?.includes('rejected') ?? application.decision_status === 'corrected'

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !busy) onClose()
      if (event.key !== 'Tab' || !dialogRef.current) return
      const focusable = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      )
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
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
  }, [busy, onClose])

  const handleSubmit = () => {
    const issues: string[] = []
    if (action === 'deny' && !reasonCodes.length) issues.push('Select at least one correction reason.')
    if (conflicts && !override.trim()) issues.push('Explain why your decision differs from the automated findings.')
    if (action === 'deny' && disposition === 'rejected' && !confirmReject) {
      issues.push('Confirm that this final rejection is intentional.')
    }
    setValidation(issues)
    if (issues.length) return

    onSubmit({
      decision: action,
      ...(action === 'deny' ? { disposition } : {}),
      reason_codes: action === 'deny' ? reasonCodes : [],
      ...(notes.trim() ? { notes: notes.trim() } : {}),
      ...(override.trim() ? { override_explanation: override.trim() } : {}),
      expected_status: application.decision_status ?? application.status,
      expected_revision: application.revision,
      idempotency_key: crypto.randomUUID(),
    })
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onClose()
    }}>
      <div
        ref={dialogRef}
        className="decision-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="decision-heading"
        aria-describedby="decision-description"
      >
        <div className="dialog-header">
          <div>
            <p className="eyebrow">Record decision</p>
            <h2 id="decision-heading" ref={headingRef} tabIndex={-1}>
              {action === 'approve' ? 'Approve application?' : 'Deny application?'}
            </h2>
          </div>
          <button className="close-button" type="button" onClick={onClose} disabled={busy} aria-label="Close decision dialog">×</button>
        </div>
        <p id="decision-description">
          Record a local review decision for <strong>{application.brand_name}</strong>. No government
          record will be updated.
        </p>

        {validation.length ? (
          <div className="error-summary" role="alert" tabIndex={-1}>
            <strong>Review the following:</strong>
            <ul>{validation.map((issue) => <li key={issue}>{issue}</li>)}</ul>
          </div>
        ) : null}
        {error ? <p className="error-banner" role="alert">{error}</p> : null}

        {action === 'deny' ? (
          <>
            <fieldset>
              <legend>Disposition</legend>
              <label className="choice-row">
                <input type="radio" name="disposition" value="needs_correction" checked={disposition === 'needs_correction'} onChange={() => setDisposition('needs_correction')} />
                <span><strong>Needs Correction</strong><small>Default; return the application with actionable reasons.</small></span>
              </label>
              {canReject ? (
                <label className="choice-row">
                  <input type="radio" name="disposition" value="rejected" checked={disposition === 'rejected'} onChange={() => setDisposition('rejected')} />
                  <span><strong>Rejected</strong><small>Final status; use only for an eligible corrected application.</small></span>
                </label>
              ) : null}
            </fieldset>
            <fieldset>
              <legend>Reasons</legend>
              {suggestedReasons.length ? suggestedReasons.map((check) => (
                <label className="check-choice" key={check.id}>
                  <input
                    type="checkbox"
                    checked={reasonCodes.includes(check.id)}
                    onChange={(event) => setReasonCodes((current) => event.target.checked
                      ? [...current, check.id]
                      : current.filter((id) => id !== check.id))}
                  />
                  <span>{check.label} <small>Suggested from {humanize(check.status)}</small></span>
                </label>
              )) : <p>No reasons were suggested by the automated findings.</p>}
            </fieldset>
            {disposition === 'rejected' ? (
              <label className="check-choice strong-confirm">
                <input type="checkbox" checked={confirmReject} onChange={(event) => setConfirmReject(event.target.checked)} />
                  <span>I understand that Rejected is a final status.</span>
              </label>
            ) : null}
          </>
        ) : null}

        {conflicts ? (
          <label className="field-label" htmlFor="override">
            Override explanation <span aria-hidden="true">*</span>
            <textarea id="override" value={override} onChange={(event) => setOverride(event.target.value)} rows={3} aria-describedby="override-help" />
            <small id="override-help">Required because this action differs from the automated findings.</small>
          </label>
        ) : null}
        <label className="field-label" htmlFor="decision-notes">
          Notes <span className="optional">Optional</span>
          <textarea id="decision-notes" value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>

        <div className="dialog-actions">
          <button className="button button-quiet" type="button" onClick={onClose} disabled={busy}>Cancel</button>
          <button className={action === 'deny' ? 'button button-danger' : 'button button-primary'} type="button" onClick={handleSubmit} disabled={busy}>
            {busy ? 'Sending…' : action === 'approve' ? 'Confirm approval' : 'Confirm denial'}
          </button>
        </div>
      </div>
    </div>
  )
}
