import { beforeEach, describe, expect, it, vi } from 'vitest'
import { confirmApplicationMatch, getReadiness, verifyPhotos } from './api'

describe('API client', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
  })

  it('sends photos as repeated multipart fields with the persisted demo session', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      verification_id: 'ver_1', processing_status: 'complete', identification_status: 'no_match',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    const files = [
      new File(['front'], 'front.png', { type: 'image/png' }),
      new File(['back'], 'back.jpg', { type: 'image/jpeg' }),
    ]

    await verifyPhotos(files)

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/v1/enforcement-items/verifications')
    expect(init.method).toBe('POST')
    expect((init.headers as Record<string, string>)['X-Demo-Session']).toBeTruthy()
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).getAll('images')).toHaveLength(2)
    expect((init.headers as Record<string, string>)['Content-Type']).toBeUndefined()
  })

  it('uses the candidate endpoint without rerunning OCR', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({
      verification_id: 'ver_1', processing_status: 'complete', identification_status: 'matched',
    }), { status: 200, headers: { 'Content-Type': 'application/json' } }))

    await confirmApplicationMatch('ver_1', 'mock_one')

    expect(fetchMock).toHaveBeenCalledWith('/api/v1/verifications/ver_1/application-match', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ application_id: 'mock_one' }),
    }))
  })

  it('treats a successful warmup response as ready', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ status: 'ready' }), { status: 200 }))
    await expect(getReadiness()).resolves.toBe(true)
  })
})
