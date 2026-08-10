import type { VerificationResponse } from '../types'

export const matchedVerification: VerificationResponse = {
  request_id: 'req_1',
  verification_id: 'ver_1',
  processing_status: 'complete',
  identification_status: 'matched',
  overall_status: 'mismatch',
  timing: { total_ms: 1840 },
  application: {
    application_id: 'mock_ttb_24001001000001',
    revision: 1,
    status: 'assigned',
    brand_name: 'North Star',
    fanciful_name: 'Reserve',
    class_type: 'Bourbon Whisky',
    net_contents: '750 mL',
    alcohol_by_volume: '40% alc./vol.',
    applicant_name: 'Sample Spirits LLC',
    registry_detail_url: 'https://example.test/public-cola/mock_ttb_24001001000001',
    registry_snapshot_date: '2026-08-09',
    score: 0.96,
    match_evidence: [
      { type: 'brand_name', value: 'North Star', confidence: 0.98 },
      { type: 'net_contents', value: '750 mL', confidence: 0.94 },
    ],
  },
  checks: [
    {
      id: 'government_warning.text',
      label: 'Government warning statement',
      status: 'mismatch',
      expected: 'Required exact warning statement',
      observed: 'GOVERNMENT WARNING: partial text',
      reason: 'The observed statement is missing required language.',
      applicability: { status: 'applied', reason: 'Required on distilled-spirits containers.' },
      evidence: [{ image_id: 'img_1', image_name: 'back.png', text: 'GOVERNMENT WARNING' }],
      source: { label: '27 CFR 16.21', url: 'https://www.ecfr.gov/current/title-27/section-16.21' },
    },
    {
      id: 'alcohol_content',
      label: 'Alcohol content',
      status: 'pass',
      expected: '40% alc./vol.',
      observed: '40% alc./vol.',
      reason: 'The values agree.',
      applicability: { status: 'applied', reason: 'Alcohol content is required for this class.' },
    },
  ],
  allowed_dispositions: ['needs_correction'],
}

export const ambiguousVerification: VerificationResponse = {
  verification_id: 'ver_ambiguous',
  processing_status: 'complete',
  identification_status: 'needs_identification',
  candidates: [
    {
      application_id: 'mock_one', revision: 1, status: 'assigned', brand_name: 'North Star',
      class_type: 'Bourbon Whisky', net_contents: '750 mL', score: 0.81,
      distinguishing_fields: { class_type: 'Bourbon Whisky', net_contents: '750 mL' },
    },
    {
      application_id: 'mock_two', revision: 2, status: 'corrected', brand_name: 'North Star Gold',
      class_type: 'Whisky', net_contents: '1 L', score: 0.79,
      distinguishing_fields: { class_type: 'Whisky', net_contents: '1 L' },
    },
  ],
}
