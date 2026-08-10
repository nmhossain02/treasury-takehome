import type { VerificationWorkflow } from '../hooks/useVerificationWorkflow'
import { CheckResults } from './CheckResults'
import { ApplicationCard, CandidateList } from './Identification'

interface VerificationWorkspaceProps {
  workflow: VerificationWorkflow
}

function elapsedLabel(milliseconds?: number): string | null {
  if (milliseconds === undefined) return null
  return milliseconds < 1_000
    ? `${milliseconds} ms`
    : `${(milliseconds / 1_000).toFixed(1)} s`
}

function EmptyWorkspace() {
  return (
    <div className="empty-result">
      <span aria-hidden="true">⌕</span>
      <div>
        <h2>Verification results</h2>
        <p>Your matched application, label checks, and supporting evidence will appear here.</p>
      </div>
    </div>
  )
}

function NoMatch({ onAddPhotos }: { onAddPhotos: () => void }) {
  return (
    <section className="no-match" aria-labelledby="no-match-heading">
      <span aria-hidden="true">?</span>
      <div>
        <p className="eyebrow">No credible match</p>
        <h2 id="no-match-heading">Add a clearer identifying view</h2>
        <p>
          Try the front brand name, back details, alcohol content, net contents, or
          producer/importer text. Verification stops when the evidence is weak.
        </p>
        <button className="button button-secondary" type="button" onClick={onAddPhotos}>
          Add more photos
        </button>
      </div>
    </section>
  )
}

function DecisionPanel({ workflow }: VerificationWorkspaceProps) {
  return (
    <section className="decision-panel" aria-labelledby="decision-panel-heading">
      <div>
        <p className="eyebrow">Human decision</p>
        <h2 id="decision-panel-heading">Record disposition</h2>
        <p>Review the findings and evidence before choosing an action.</p>
      </div>
      <div className="decision-buttons">
        <button className="button button-primary" type="button" onClick={() => workflow.openDecision('approve')}>
          Approve
        </button>
        <button className="button button-danger-outline" type="button" onClick={() => workflow.openDecision('deny')}>
          Deny
        </button>
      </div>
    </section>
  )
}

function ReceiptPanel({ workflow }: VerificationWorkspaceProps) {
  const receipt = workflow.receipt!
  return (
    <section className="receipt-card" aria-labelledby="receipt-heading">
      <span className="receipt-check" aria-hidden="true">✓</span>
      <div>
        <p className="eyebrow">Review complete</p>
        <h2 id="receipt-heading">Disposition recorded</h2>
        <p className="receipt-next">The completed item has been cleared. Intake is ready for the next label.</p>
        <dl>
          <div><dt>New status</dt><dd>{receipt.new_status.replaceAll('_', ' ')}</dd></div>
          <div><dt>Receipt ID</dt><dd>{receipt.receipt_id}</dd></div>
          <div><dt>Recorded</dt><dd>{new Date(receipt.decided_at).toLocaleString()}</dd></div>
        </dl>
        <button className="button button-primary" type="button" onClick={workflow.choosePhotos}>
          Add next label photos
        </button>
      </div>
    </section>
  )
}

export function VerificationWorkspace({ workflow }: VerificationWorkspaceProps) {
  const {
    busyLabel,
    confirmCandidate,
    elapsed,
    hasConfirmedResult,
    isBusy,
    requestError,
    resultsRef,
    runVerification,
    choosePhotos,
    verification,
  } = workflow

  return (
    <section className="result-column" aria-label="Verification workspace">
      <div className="live-status" role="status" aria-live="polite" aria-atomic="true">
        {busyLabel ? (
          <>
            <span className="spinner" aria-hidden="true" />
            <strong>{busyLabel}</strong>
            <span>{(elapsed / 1_000).toFixed(1)} seconds</span>
          </>
        ) : null}
      </div>

      {requestError ? (
        <div className="error-banner request-error" role="alert">
          <strong>Verification could not finish.</strong> {requestError}{' '}
          <button className="text-button" type="button" onClick={() => void runVerification()}>
            Try again
          </button>
        </div>
      ) : null}

      {!verification && !busyLabel && !workflow.receipt ? <EmptyWorkspace /> : null}

      {!verification && workflow.receipt ? (
        <div className="review-workspace" ref={resultsRef} tabIndex={-1} aria-label="Completed review">
          <div className="review-scroll receipt-state" tabIndex={0}>
            <ReceiptPanel workflow={workflow} />
          </div>
        </div>
      ) : null}

      {verification ? (
        <div className="review-workspace" ref={resultsRef} tabIndex={-1} aria-label="Verification result">
          <div className="review-scroll" tabIndex={0} aria-label="Verification details">
            {verification.processing_status === 'partial' ? (
              <p className="partial-banner" role="status">
                <strong>Partial result:</strong> Some photos or checks could not finish. Review
                uncertainty before acting.
              </p>
            ) : null}

            {verification.identification_status === 'needs_identification' ? (
              <CandidateList
                candidates={verification.candidates ?? []}
                busy={isBusy}
                onConfirm={(id) => void confirmCandidate(id)}
                onAddPhotos={choosePhotos}
              />
            ) : null}

            {verification.identification_status === 'no_match' ? (
              <NoMatch onAddPhotos={choosePhotos} />
            ) : null}

            {hasConfirmedResult ? (
              <>
                <ApplicationCard application={verification.application!} />
                <CheckResults checks={verification.checks ?? []} />
                <div className="rerun-row">
                  <button className="text-button" type="button" onClick={choosePhotos}>
                    Change photos
                  </button>
                  {verification.timing?.total_ms !== undefined ? (
                    <span>Processed in {elapsedLabel(verification.timing.total_ms)}</span>
                  ) : null}
                </div>
              </>
            ) : null}
          </div>
          {hasConfirmedResult ? <DecisionPanel workflow={workflow} /> : null}
        </div>
      ) : null}
    </section>
  )
}
