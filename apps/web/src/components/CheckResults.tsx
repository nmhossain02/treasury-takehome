import type { CheckResult, CheckStatus } from '../types'

const statusDetails: Record<CheckStatus, { label: string; icon: string }> = {
  pass: { label: 'Pass', icon: '✓' },
  mismatch: { label: 'Mismatch', icon: '!' },
  needs_review: { label: 'Needs review', icon: '?' },
}

function sourceView(source: CheckResult['source']) {
  if (!source) return null
  if (typeof source === 'string') return <span>{source}</span>
  if (source.url) {
    return <a href={source.url} target="_blank" rel="noreferrer">{source.label ?? 'Rule source'}</a>
  }
  return <span>{source.label}</span>
}

export function CheckResults({ checks }: { checks: CheckResult[] }) {
  const counts = checks.reduce<Record<CheckStatus, number>>(
    (summary, check) => ({ ...summary, [check.status]: summary[check.status] + 1 }),
    { mismatch: 0, needs_review: 0, pass: 0 },
  )

  return (
    <section className="results-section" aria-labelledby="results-heading">
      <div className="section-heading results-heading-row">
        <div>
          <p className="eyebrow">Automated findings</p>
          <h2 id="results-heading">Cross-reference results</h2>
        </div>
        <div className="result-counts" aria-label="Finding totals">
          <span className="count mismatch"><strong>{counts.mismatch}</strong> mismatch</span>
          <span className="count review"><strong>{counts.needs_review}</strong> review</span>
          <span className="count pass"><strong>{counts.pass}</strong> pass</span>
        </div>
      </div>

      <ol className="check-list">
        {checks.map((check) => {
          const detail = statusDetails[check.status]
          return (
            <li key={check.id} className={`check-card status-${check.status}`}>
              <div className="check-header">
                <span className="status-icon" aria-hidden="true">{detail.icon}</span>
                <div>
                  <span className="status-label">{detail.label}</span>
                  <h3>{check.label}</h3>
                </div>
              </div>
              <p>{check.reason}</p>
              <details className="check-details">
                <summary>{check.status === 'pass' ? 'View comparison' : 'Review details'}</summary>
                <div className="check-detail-content">
                  {(check.expected || check.observed) && (
                    <dl className="comparison">
                      <div><dt>Expected</dt><dd>{check.expected ?? 'Not available'}</dd></div>
                      <div><dt>Observed</dt><dd>{check.observed ?? 'Could not determine'}</dd></div>
                    </dl>
                  )}
                  {check.applicability ? (
                    <p className="applicability">
                      <strong>{check.applicability.status === 'applied' ? 'Applied' : check.applicability.status === 'skipped' ? 'Skipped' : 'Could not evaluate'}:</strong>{' '}
                      {check.applicability.reason}
                    </p>
                  ) : null}
                  {check.evidence?.length ? (
                    <div className="photo-evidence">
                      <h4>Photo evidence ({check.evidence.length})</h4>
                      <ul className="evidence-list">
                        {check.evidence.map((evidence, index) => (
                          <li key={`${evidence.image_id}-${index}`}>
                            <span>{evidence.image_name ?? evidence.image_id ?? `Photo ${index + 1}`}</span>
                            <q>{evidence.text ?? 'No readable text'}</q>
                            {evidence.location ? <small>{evidence.location}</small> : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {check.source ? <p className="rule-source">Rule source: {sourceView(check.source)}</p> : null}
                </div>
              </details>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
