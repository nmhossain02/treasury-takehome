import { getDemoSessionId } from './session'
import type {
  Capabilities,
  DecisionReceipt,
  DecisionRequest,
  VerificationResponse,
} from './types'

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly requestId?: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function readResponse<T>(response: Response): Promise<T> {
  if (response.ok) return response.json() as Promise<T>

  let message = 'The request could not be completed.'
  try {
    const body = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>
      message?: string
      request_id?: string
    }
    if (typeof body.detail === 'string') message = body.detail
    else if (Array.isArray(body.detail)) {
      message = body.detail.map((item) => item.msg).filter(Boolean).join(' ') || message
    } else if (body.message) message = body.message
    throw new ApiError(message, response.status, body.request_id)
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(message, response.status)
  }
}

function headers(withJson = false): HeadersInit {
  return {
    'X-Demo-Session': getDemoSessionId(),
    ...(withJson ? { 'Content-Type': 'application/json' } : {}),
  }
}

export async function getCapabilities(signal?: AbortSignal): Promise<Capabilities> {
  const response = await fetch('/api/v1/capabilities', {
    headers: headers(),
    signal,
  })
  return readResponse<Capabilities>(response)
}

export async function getReadiness(signal?: AbortSignal): Promise<boolean> {
  const response = await fetch('/health/ready', {
    headers: headers(),
    signal,
  })
  if (!response.ok) return false
  const body = (await response.json()) as { ready?: boolean; status?: string }
  return body.ready !== false && body.status !== 'not_ready'
}

export async function verifyPhotos(
  files: File[],
  signal?: AbortSignal,
): Promise<VerificationResponse> {
  const body = new FormData()
  files.forEach((file) => body.append('images', file, file.name))
  const response = await fetch('/api/v1/enforcement-items/verifications', {
    method: 'POST',
    headers: headers(),
    body,
    signal,
  })
  return readResponse<VerificationResponse>(response)
}

export async function confirmApplicationMatch(
  verificationId: string,
  applicationId: string,
  signal?: AbortSignal,
): Promise<VerificationResponse> {
  const response = await fetch(
    `/api/v1/verifications/${encodeURIComponent(verificationId)}/application-match`,
    {
      method: 'POST',
      headers: headers(true),
      body: JSON.stringify({ application_id: applicationId }),
      signal,
    },
  )
  return readResponse<VerificationResponse>(response)
}

export async function submitDecision(
  verificationId: string,
  decision: DecisionRequest,
  signal?: AbortSignal,
): Promise<DecisionReceipt> {
  const response = await fetch(
    `/api/v1/verifications/${encodeURIComponent(verificationId)}/decisions`,
    {
      method: 'POST',
      headers: headers(true),
      body: JSON.stringify(decision),
      signal,
    },
  )
  return readResponse<DecisionReceipt>(response)
}
