import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { ambiguousVerification, matchedVerification } from './test/fixtures'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

describe('photo-only verification workflow', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({ max_file_bytes: 1_500_000 }))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
  })

  it('submits photos without application fields and shows explainable results', async () => {
    const user = userEvent.setup()
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({ max_file_bytes: 1_500_000 }))
      if (url === '/api/v1/enforcement-items/verifications') return Promise.resolve(jsonResponse(matchedVerification))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)

    expect(screen.getByText(/public COLA metadata/i)).toBeInTheDocument()
    expect(screen.queryByLabelText(/application/i)).not.toBeInTheDocument()
    await user.upload(
      screen.getByLabelText('Choose enforcement photos'),
      new File(['image'], 'back.png', { type: 'image/png' }),
    )
    await user.click(screen.getByRole('button', { name: 'Verify label' }))

    expect(await screen.findByRole('heading', { name: 'North Star' })).toBeInTheDocument()
    expect(screen.getByText('96% match confidence')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /View public record/i })).toHaveClass('button')
    expect(screen.getByRole('heading', { name: 'Cross-reference results' })).toBeInTheDocument()
    expect(screen.getByText('The observed statement is missing required language.')).toBeInTheDocument()
    expect(screen.getByText(/Required on distilled-spirits containers/)).toBeInTheDocument()
    expect(screen.getByText('Review details').closest('details')).not.toHaveAttribute('open')
  })

  it('chooses a bundled sample set and sends it through the normal verification flow', async () => {
    const user = userEvent.setup()
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({ max_file_bytes: 1_500_000 }))
      if (url.includes('seven-fathoms-')) {
        return Promise.resolve(new Response(new Uint8Array([255, 216, 255]), {
          headers: { 'Content-Type': 'image/jpeg' },
        }))
      }
      if (url === '/api/v1/enforcement-items/verifications') return Promise.resolve(jsonResponse(matchedVerification))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Try a sample' }))
    const chooser = screen.getByRole('dialog', { name: 'Choose sample label photos' })
    expect(within(chooser).getAllByRole('button')).toHaveLength(5)
    await user.click(within(chooser).getByRole('button', { name: /Seven Fathoms/i }))

    expect(await screen.findAllByRole('img', { name: /Selected photo/ })).toHaveLength(2)
    await user.click(screen.getByRole('button', { name: 'Verify label' }))
    expect(await screen.findByRole('heading', { name: 'North Star' })).toBeInTheDocument()
    const verificationCall = fetchMock.mock.calls.find(
      ([url]) => url === '/api/v1/enforcement-items/verifications',
    )
    const images = (verificationCall?.[1].body as FormData).getAll('images') as File[]
    expect(images.map((image) => image.name)).toEqual([
      'seven-fathoms-front.jpg',
      'seven-fathoms-back.jpg',
    ])
  })

  it('clears stale results as soon as another verification is submitted', async () => {
    const user = userEvent.setup()
    let verificationCalls = 0
    let finishSecond: ((response: Response) => void) | undefined
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({}))
      if (url === '/api/v1/enforcement-items/verifications') {
        verificationCalls += 1
        if (verificationCalls === 1) return Promise.resolve(jsonResponse(matchedVerification))
        return new Promise<Response>((resolve) => { finishSecond = resolve })
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)
    await user.upload(screen.getByLabelText('Choose enforcement photos'), new File(['x'], 'front.png', { type: 'image/png' }))
    await user.click(screen.getByRole('button', { name: 'Verify label' }))
    await screen.findByRole('heading', { name: 'North Star' })

    await user.click(screen.getByRole('button', { name: 'Run again' }))

    expect(screen.queryByRole('heading', { name: 'North Star' })).not.toBeInTheDocument()
    expect(screen.getByText(/Reading photos and matching/i)).toBeInTheDocument()
    finishSecond?.(jsonResponse(matchedVerification))
    expect(await screen.findByRole('heading', { name: 'North Star' })).toBeInTheDocument()
  })

  it('resolves an ambiguous result through one of at most three candidates', async () => {
    const user = userEvent.setup()
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({}))
      if (url === '/api/v1/enforcement-items/verifications') return Promise.resolve(jsonResponse(ambiguousVerification))
      if (url.includes('/application-match')) return Promise.resolve(jsonResponse(matchedVerification))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)
    await user.upload(screen.getByLabelText('Choose enforcement photos'), new File(['x'], 'front.jpg', { type: 'image/jpeg' }))
    await user.click(screen.getByRole('button', { name: 'Verify label' }))

    const heading = await screen.findByRole('heading', { name: 'A few records look similar' })
    const section = heading.closest('section')!
    expect(within(section).getAllByRole('button', { name: 'Use this record' })).toHaveLength(2)
    await user.click(within(section).getAllByRole('button', { name: 'Use this record' })[0])

    await screen.findByRole('heading', { name: 'Cross-reference results' })
    const matchCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/application-match'))
    expect(JSON.parse(matchCall?.[1].body as string)).toEqual({ application_id: 'mock_one' })
  })

  it('defaults denial to Needs Correction and displays the mock receipt', async () => {
    const user = userEvent.setup()
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.resolve(jsonResponse({ status: 'ready' }))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({}))
      if (url === '/api/v1/enforcement-items/verifications') return Promise.resolve(jsonResponse(matchedVerification))
      if (url.includes('/decisions')) return Promise.resolve(jsonResponse({
        mock: true,
        receipt_id: 'mock_receipt_1',
        application_id: 'mock_ttb_24001001000001',
        decision: 'deny',
        prior_status: 'assigned',
        new_status: 'needs_correction',
        revision: 2,
        decided_at: '2026-08-06T20:00:00Z',
      }))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)
    await user.upload(screen.getByLabelText('Choose enforcement photos'), new File(['x'], 'front.png', { type: 'image/png' }))
    await user.click(screen.getByRole('button', { name: 'Verify label' }))
    await screen.findByRole('heading', { name: 'Cross-reference results' })
    await user.click(screen.getByRole('button', { name: 'Deny' }))

    const dialog = screen.getByRole('dialog')
    expect(within(dialog).getByRole('radio', { name: /Needs Correction/i })).toBeChecked()
    await user.click(within(dialog).getByRole('button', { name: 'Confirm denial' }))

    expect(await screen.findByRole('heading', { name: 'Disposition recorded' })).toBeInTheDocument()
    expect(screen.getByText('mock_receipt_1')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'North Star' })).not.toBeInTheDocument()
    expect(screen.getByText('Add photos to begin')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Verify label' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Add next label photos' })).toBeEnabled()
    expect(screen.queryByText(/state may reset/i)).not.toBeInTheDocument()
    const decisionCall = fetchMock.mock.calls.find(([url]) => String(url).includes('/decisions'))
    const body = JSON.parse(decisionCall?.[1].body as string)
    expect(body).toMatchObject({ decision: 'deny', disposition: 'needs_correction', reason_codes: ['government_warning.text'] })
  })

  it('presents a concise, self-contained empty workspace', async () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: 'Verify a product label' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Verification results' })).toBeInTheDocument()
    expect(screen.getByText('Add photos to begin')).toBeInTheDocument()
    expect(screen.queryByText(/prototype reads/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/ephemeral demo state/i)).not.toBeInTheDocument()
  })

  it('opens a concise usage guide from the header and returns focus when closed', async () => {
    const user = userEvent.setup()
    render(<App />)

    const trigger = screen.getByRole('button', { name: 'How to use Label Lens' })
    await user.click(trigger)
    const guide = screen.getByRole('dialog', { name: 'How Label Lens works' })
    expect(within(guide).getByText('Upload images')).toBeInTheDocument()
    expect(within(guide).getByText('Label Lens finds a matching COLA')).toBeInTheDocument()
    expect(within(guide).getByText('Choose mock approve or deny')).toBeInTheDocument()
    expect(within(guide).getByText(/Nothing is sent to a government system/i)).toBeInTheDocument()

    await user.click(within(guide).getByRole('button', { name: 'Got it' }))
    expect(screen.queryByRole('dialog', { name: 'How Label Lens works' })).not.toBeInTheDocument()
    await waitFor(() => expect(trigger).toHaveFocus())
  })

  it('keeps intake available when readiness cannot be confirmed and supports retry', async () => {
    fetchMock.mockImplementation((url: string) => {
      if (url === '/health/ready') return Promise.reject(new Error('cold start'))
      if (url === '/api/v1/capabilities') return Promise.resolve(jsonResponse({}))
      return Promise.reject(new Error(`Unexpected URL: ${url}`))
    })
    render(<App />)

    expect(await screen.findByText('Readiness unconfirmed')).toBeInTheDocument()
    expect(screen.getByLabelText('Choose enforcement photos')).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Retry' })).toBeEnabled()
    await waitFor(() => expect(screen.getByText(/public COLA metadata/i)).toBeVisible())
  })
})
