import type { ApplicationSummary, MatchCandidate } from '../types'

interface ApplicationCardProps {
  application: ApplicationSummary
}

function humanize(value: string): string {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function Confidence({ score }: { score?: number }) {
  if (score === undefined) return null
  return <span className="confidence">{Math.round(score * 100)}% match confidence</span>
}

export function ApplicationCard({ application }: ApplicationCardProps) {
  return (
    <section className="application-card" aria-labelledby="matched-record-heading">
      <div className="record-title-row">
        <div>
          <p className="eyebrow success-text">Application identified</p>
          <h2 id="matched-record-heading">{application.brand_name}</h2>
          {application.fanciful_name ? <p className="fanciful-name">{application.fanciful_name}</p> : null}
        </div>
        <Confidence score={application.score} />
      </div>
      <dl className="record-summary">
        <div>
          <dt>Application ID</dt>
          <dd>{application.application_id}</dd>
        </div>
        <div>
          <dt>{application.registry_status ? 'Registry status' : 'Current status'}</dt>
          <dd>{humanize(application.status)}</dd>
        </div>
        {application.applicant_name ? (
          <div><dt>Applicant</dt><dd>{application.applicant_name}</dd></div>
        ) : null}
      </dl>
      {application.registry_detail_url ? (
        <p className="registry-source">
          <a
            className="button button-secondary registry-button"
            href={application.registry_detail_url}
            target="_blank"
            rel="noreferrer"
          >
            View public record <span aria-hidden="true">↗</span>
          </a>
          {application.registry_snapshot_date ? <span>Metadata snapshot {application.registry_snapshot_date}</span> : null}
        </p>
      ) : null}
      {application.match_evidence?.length ? (
        <details className="match-evidence">
          <summary>Why this record matched ({application.match_evidence.length} signals)</summary>
          <ul>
            {application.match_evidence.map((signal, index) => (
              <li key={`${signal.type ?? signal.label}-${index}`}>
                <span>{signal.label ?? (signal.type ? humanize(signal.type) : 'Observed text')}</span>
                <strong>{signal.value ?? signal.text ?? 'Matched label evidence'}</strong>
                {signal.confidence !== undefined ? (
                  <small>{Math.round(signal.confidence * 100)}% OCR confidence</small>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  )
}

interface CandidateListProps {
  candidates: MatchCandidate[]
  busy: boolean
  onConfirm: (applicationId: string) => void
  onAddPhotos: () => void
}

export function CandidateList({ candidates, busy, onConfirm, onAddPhotos }: CandidateListProps) {
  return (
    <section className="candidate-section" aria-labelledby="candidate-heading">
      <p className="eyebrow warning-text">Confirmation needed</p>
      <h2 id="candidate-heading">A few records look similar</h2>
      <p>Compare the distinguishing facts below. Choosing a record uses the existing OCR result.</p>
      <ol className="candidate-list">
        {candidates.slice(0, 3).map((candidate) => (
          <li key={candidate.application_id} className="candidate-card">
            <div className="candidate-title">
              <div>
                <h3>{candidate.brand_name}</h3>
                <p>{candidate.application_id}</p>
              </div>
              <Confidence score={candidate.score} />
            </div>
            <dl>
              {Object.entries(candidate.distinguishing_fields ?? {}).map(([label, value]) => (
                <div key={label}>
                  <dt>{humanize(label)}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
              {!Object.keys(candidate.distinguishing_fields ?? {}).length ? (
                <>
                  <div><dt>Class / type</dt><dd>{candidate.class_type ?? 'Not available'}</dd></div>
                  <div><dt>Net contents</dt><dd>{candidate.net_contents ?? 'Not available'}</dd></div>
                </>
              ) : null}
            </dl>
            {candidate.conflicting_signals?.length ? (
              <p className="candidate-conflict">
                Conflicts: {candidate.conflicting_signals.map(humanize).join(', ')}
              </p>
            ) : null}
            <button
              className="button button-secondary"
              type="button"
              disabled={busy}
              onClick={() => onConfirm(candidate.application_id)}
            >
              Use this record
            </button>
          </li>
        ))}
      </ol>
      <button className="text-button" type="button" disabled={busy} onClick={onAddPhotos}>
        Add clearer photos instead
      </button>
    </section>
  )
}
