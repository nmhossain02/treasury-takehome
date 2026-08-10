import { useCallback, useEffect, useRef, useState } from 'react'
import {
  confirmApplicationMatch,
  getCapabilities,
  getReadiness,
  submitDecision,
  verifyPhotos,
} from '../api'
import type { SelectedPhoto } from '../components/PhotoPicker'
import { loadSamplePhotos } from '../photoSamples'
import type {
  Capabilities,
  DecisionReceipt,
  DecisionRequest,
  VerificationResponse,
} from '../types'

export type Readiness = 'preparing' | 'ready' | 'unavailable'
export type DecisionAction = 'approve' | 'deny'

function uniqueId(): string {
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
}

function messageForError(error: unknown): string {
  if (error instanceof DOMException && error.name === 'AbortError') return ''
  if (error instanceof Error) return error.message
  return 'Something went wrong. Please try again.'
}

export function useVerificationWorkflow() {
  const [capabilities, setCapabilities] = useState<Capabilities>({})
  const [readiness, setReadiness] = useState<Readiness>('preparing')
  const [photos, setPhotos] = useState<SelectedPhoto[]>([])
  const [photoError, setPhotoError] = useState('')
  const [requestError, setRequestError] = useState('')
  const [verification, setVerification] = useState<VerificationResponse | null>(null)
  const [busyLabel, setBusyLabel] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [decisionAction, setDecisionAction] = useState<DecisionAction | null>(null)
  const [decisionBusy, setDecisionBusy] = useState(false)
  const [decisionError, setDecisionError] = useState('')
  const [receipt, setReceipt] = useState<DecisionReceipt | null>(null)
  const [sampleBusy, setSampleBusy] = useState<string | null>(null)

  const photosRef = useRef<SelectedPhoto[]>([])
  const resultsRef = useRef<HTMLDivElement>(null)
  const addPhotosRef = useRef<HTMLDivElement>(null)
  const decisionTriggerRef = useRef<HTMLElement | null>(null)

  const checkReadiness = useCallback(async () => {
    setReadiness('preparing')
    try {
      setReadiness(await getReadiness() ? 'ready' : 'unavailable')
    } catch {
      setReadiness('unavailable')
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void getCapabilities(controller.signal).then(setCapabilities).catch(() => undefined)
    void checkReadiness()
    return () => controller.abort()
  }, [checkReadiness])

  useEffect(() => {
    photosRef.current = photos
  }, [photos])

  useEffect(() => () => {
    photosRef.current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl))
  }, [])

  useEffect(() => {
    if (!busyLabel) return
    const started = performance.now()
    setElapsed(0)
    const timer = window.setInterval(() => setElapsed(performance.now() - started), 100)
    return () => window.clearInterval(timer)
  }, [busyLabel])

  const resetResult = useCallback(() => {
    setVerification(null)
    setReceipt(null)
  }, [])

  const discardPhotos = useCallback(() => {
    setPhotos((current) => {
      current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl))
      return []
    })
  }, [])

  const addPhotos = useCallback((files: File[]) => {
    setPhotoError('')
    const accepted: SelectedPhoto[] = []
    const errors: string[] = []

    for (const file of files) {
      if (!['image/jpeg', 'image/png'].includes(file.type)) {
        errors.push(`${file.name} is not a JPEG or PNG.`)
      } else if (capabilities.max_file_bytes && file.size > capabilities.max_file_bytes) {
        errors.push(`${file.name} exceeds the per-photo size limit.`)
      } else {
        accepted.push({ id: uniqueId(), file, previewUrl: URL.createObjectURL(file) })
      }
    }

    const nextTotal = [...photos, ...accepted].reduce((sum, photo) => sum + photo.file.size, 0)
    if (capabilities.max_aggregate_bytes && nextTotal > capabilities.max_aggregate_bytes) {
      accepted.forEach((photo) => URL.revokeObjectURL(photo.previewUrl))
      errors.push('These photos exceed the total upload size limit.')
    } else if (accepted.length) {
      setPhotos((current) => [...current, ...accepted])
      resetResult()
    }
    setPhotoError(errors.join(' '))
  }, [capabilities.max_aggregate_bytes, capabilities.max_file_bytes, photos, resetResult])

  const useSamplePhotos = useCallback(async (sampleId: string) => {
    setSampleBusy(sampleId)
    setPhotoError('')
    try {
      const files = await loadSamplePhotos(sampleId)
      const totalBytes = files.reduce((sum, file) => sum + file.size, 0)
      if (files.some((file) => capabilities.max_file_bytes && file.size > capabilities.max_file_bytes)) {
        throw new Error('A sample photo exceeds the current per-photo size limit.')
      }
      if (capabilities.max_aggregate_bytes && totalBytes > capabilities.max_aggregate_bytes) {
        throw new Error('The sample photos exceed the current total upload limit.')
      }
      const selected = files.map((file, index) => ({
        id: `${uniqueId()}-${index}`,
        file,
        previewUrl: URL.createObjectURL(file),
      }))
      setPhotos((current) => {
        current.forEach((photo) => URL.revokeObjectURL(photo.previewUrl))
        return selected
      })
      resetResult()
    } catch (error) {
      setPhotoError(messageForError(error))
    } finally {
      setSampleBusy(null)
    }
  }, [capabilities.max_aggregate_bytes, capabilities.max_file_bytes, resetResult])

  const removePhoto = useCallback((id: string) => {
    setPhotos((current) => {
      const removed = current.find((photo) => photo.id === id)
      if (removed) URL.revokeObjectURL(removed.previewUrl)
      return current.filter((photo) => photo.id !== id)
    })
    resetResult()
  }, [resetResult])

  const clearPhotos = useCallback(() => {
    discardPhotos()
    resetResult()
    setPhotoError('')
    window.setTimeout(
      () => addPhotosRef.current?.querySelector<HTMLButtonElement>('button')?.focus(),
      0,
    )
  }, [discardPhotos, resetResult])

  const scrollToPhotos = useCallback(() => {
    addPhotosRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])

  const choosePhotos = useCallback(() => {
    const intake = addPhotosRef.current
    intake?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    const input = intake?.querySelector<HTMLInputElement>('input[type="file"]')
    if (input && !input.disabled) input.click()
  }, [])

  const focusResults = useCallback(() => {
    window.setTimeout(() => resultsRef.current?.focus(), 0)
  }, [])

  const runVerification = useCallback(async () => {
    if (!photos.length) {
      setPhotoError('Add at least one JPEG or PNG photo to continue.')
      scrollToPhotos()
      return
    }

    setRequestError('')
    resetResult()
    setBusyLabel(readiness === 'preparing'
      ? 'Preparing verifier…'
      : 'Reading photos and matching an application…')
    try {
      if (readiness === 'preparing') await getReadiness().catch(() => false)
      setVerification(await verifyPhotos(photos.map((photo) => photo.file)))
      focusResults()
    } catch (error) {
      setRequestError(messageForError(error))
    } finally {
      setBusyLabel('')
    }
  }, [focusResults, photos, readiness, resetResult, scrollToPhotos])

  const confirmCandidate = useCallback(async (applicationId: string) => {
    if (!verification) return
    setRequestError('')
    setBusyLabel('Confirming record and running cross-references…')
    try {
      setVerification(await confirmApplicationMatch(verification.verification_id, applicationId))
      focusResults()
    } catch (error) {
      setRequestError(messageForError(error))
    } finally {
      setBusyLabel('')
    }
  }, [focusResults, verification])

  const openDecision = useCallback((action: DecisionAction) => {
    decisionTriggerRef.current = document.activeElement as HTMLElement
    setDecisionError('')
    setDecisionAction(action)
  }, [])

  const closeDecision = useCallback(() => {
    setDecisionAction(null)
    window.setTimeout(() => decisionTriggerRef.current?.focus(), 0)
  }, [])

  const handleDecision = useCallback(async (request: DecisionRequest) => {
    if (!verification) return
    setDecisionBusy(true)
    setDecisionError('')
    try {
      const completedReceipt = await submitDecision(verification.verification_id, request)
      discardPhotos()
      setVerification(null)
      setPhotoError('')
      setReceipt(completedReceipt)
      setDecisionAction(null)
      focusResults()
    } catch (error) {
      setDecisionError(messageForError(error))
    } finally {
      setDecisionBusy(false)
    }
  }, [discardPhotos, focusResults, verification])

  const isBusy = Boolean(busyLabel)
  const hasConfirmedResult = verification?.identification_status === 'matched'
    && Boolean(verification.application)

  return {
    capabilities,
    readiness,
    photos,
    photoError,
    requestError,
    verification,
    busyLabel,
    elapsed,
    decisionAction,
    decisionBusy,
    decisionError,
    receipt,
    sampleBusy,
    isBusy,
    hasConfirmedResult,
    resultsRef,
    addPhotosRef,
    checkReadiness,
    addPhotos,
    useSamplePhotos,
    removePhoto,
    clearPhotos,
    scrollToPhotos,
    choosePhotos,
    runVerification,
    confirmCandidate,
    openDecision,
    closeDecision,
    handleDecision,
  }
}

export type VerificationWorkflow = ReturnType<typeof useVerificationWorkflow>
