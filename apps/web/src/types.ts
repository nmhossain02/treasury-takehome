export type ProcessingStatus = 'complete' | 'partial' | 'failed'
export type IdentificationStatus = 'matched' | 'needs_identification' | 'no_match'
export type CheckStatus = 'pass' | 'mismatch' | 'needs_review'
export type ApplicabilityStatus = 'applied' | 'skipped' | 'unable'

export interface Capabilities {
  supported_categories?: string[]
  accepted_media_types?: string[]
  max_file_bytes?: number
  max_aggregate_bytes?: number
  ruleset?: { id?: string; version?: string } | string
  ocr_strategies?: Array<string | { id: string; active?: boolean }>
}

export interface MatchSignal {
  label?: string
  type?: string
  value?: string
  text?: string
  confidence?: number
  contribution?: number
  evidence_ref?: string
}

export interface ApplicationSummary {
  application_id: string
  revision: number
  status: string
  decision_status?: string
  registry_status?: string
  registry_snapshot_date?: string
  registry_detail_url?: string
  data_source?: 'synthetic' | 'ttb_public_registry'
  brand_name: string
  fanciful_name?: string | null
  class_type?: string | null
  net_contents?: string | null
  alcohol_by_volume?: string | null
  applicant_name?: string
  score?: number
  match_evidence?: MatchSignal[]
  distinguishing_fields?: Record<string, string | number | boolean | null>
}

export interface MatchCandidate extends ApplicationSummary {
  supporting_signals?: MatchSignal[]
  conflicting_signals?: string[]
}

export interface EvidenceItem {
  image_id?: string
  image_name?: string
  text?: string
  confidence?: number
  location?: string
}

export interface Applicability {
  status: ApplicabilityStatus
  reason: string
}

export interface CheckResult {
  id: string
  label: string
  status: CheckStatus
  observed?: string | null
  expected?: string | null
  reason: string
  source?: { label?: string; url?: string } | string
  applicability?: Applicability
  evidence?: EvidenceItem[]
}

export interface VerificationResponse {
  request_id?: string
  verification_id: string
  processing_status: ProcessingStatus
  identification_status: IdentificationStatus
  application?: ApplicationSummary | null
  candidates?: MatchCandidate[]
  overall_status?: CheckStatus
  checks?: CheckResult[]
  applicability_plan?: Array<{
    check_id: string
    label?: string
    status: ApplicabilityStatus
    reason: string
  }>
  ruleset?: { id?: string; version?: string }
  timing?: { total_ms?: number; [stage: string]: number | undefined }
  allowed_dispositions?: Array<'needs_correction' | 'rejected'>
}

export interface DecisionRequest {
  decision: 'approve' | 'deny'
  disposition?: 'needs_correction' | 'rejected'
  reason_codes: string[]
  notes?: string
  override_explanation?: string
  expected_status: string
  expected_revision: number
  idempotency_key: string
}

export interface DecisionReceipt {
  mock: true
  receipt_id: string
  application_id: string
  decision: 'approve' | 'deny'
  prior_status: string
  new_status: string
  revision: number
  decided_at: string
}
