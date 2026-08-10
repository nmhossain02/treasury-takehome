import { useEffect, useRef, useState } from 'react'
import { SAMPLE_PHOTO_SETS } from '../photoSamples'

export interface SelectedPhoto {
  id: string
  file: File
  previewUrl: string
}

interface PhotoPickerProps {
  photos: SelectedPhoto[]
  disabled: boolean
  maxFileBytes?: number
  maxAggregateBytes?: number
  sampleBusy: string | null
  onAdd: (files: File[]) => void
  onUseSample: (sampleId: string) => void
  onRemove: (id: string) => void
  onClear: () => void
}

function formatBytes(bytes: number): string {
  if (bytes < 1_000_000) return `${Math.ceil(bytes / 1_000)} KB`
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

export function PhotoPicker({
  photos,
  disabled,
  maxFileBytes,
  maxAggregateBytes,
  sampleBusy,
  onAdd,
  onUseSample,
  onRemove,
  onClear,
}: PhotoPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const samplePickerRef = useRef<HTMLDivElement>(null)
  const [dragging, setDragging] = useState(false)
  const [samplesOpen, setSamplesOpen] = useState(false)
  const totalBytes = photos.reduce((sum, photo) => sum + photo.file.size, 0)

  useEffect(() => {
    if (!samplesOpen) return
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!samplePickerRef.current?.contains(event.target as Node)) setSamplesOpen(false)
    }
    document.addEventListener('mousedown', closeOnOutsideClick)
    return () => document.removeEventListener('mousedown', closeOnOutsideClick)
  }, [samplesOpen])

  useEffect(() => {
    if (disabled) setSamplesOpen(false)
  }, [disabled])

  const acceptFiles = (list: FileList | null) => {
    if (!list) return
    onAdd(Array.from(list))
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <section className="photo-picker" aria-labelledby="photo-heading">
      <div className="photo-picker-heading">
        <div>
          <p className="eyebrow">Label photos</p>
          <h2 id="photo-heading">Add photos</h2>
        </div>
        <div
          className="sample-picker"
          ref={samplePickerRef}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setSamplesOpen(false)
              samplePickerRef.current?.querySelector<HTMLButtonElement>('.sample-button')?.focus()
            }
          }}
        >
          <button
            className="sample-button"
            type="button"
            disabled={disabled || Boolean(sampleBusy)}
            aria-haspopup="dialog"
            aria-expanded={samplesOpen}
            onClick={() => setSamplesOpen((open) => !open)}
          >
            <span aria-hidden="true">▧</span>
            {sampleBusy ? 'Loading…' : 'Try a sample'}
          </button>
          {samplesOpen ? (
            <div className="sample-menu" role="dialog" aria-label="Choose sample label photos">
              <p>Choose a public COLA label set</p>
              <div>
                {SAMPLE_PHOTO_SETS.map((sample) => (
                  <button
                    type="button"
                    key={sample.id}
                    onClick={() => {
                      setSamplesOpen(false)
                      onUseSample(sample.id)
                    }}
                  >
                    <span>
                      <strong>{sample.name}</strong>
                      <small>{sample.description}</small>
                    </span>
                    <small>{sample.photoCount} photos</small>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
      <p className="section-copy">
        Include the front, back, and required statements when available.
      </p>

      <div
        className={`drop-zone${dragging ? ' is-dragging' : ''}`}
        onDragEnter={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false)
        }}
        onDrop={(event) => {
          event.preventDefault()
          setDragging(false)
          if (!disabled) acceptFiles(event.dataTransfer.files)
        }}
      >
        <span className="upload-mark" aria-hidden="true">↑</span>
        <div className="drop-message">
          <strong>Drop label photos here</strong>
          <span>JPEG or PNG · multiple files welcome</span>
        </div>
        <button
          className="button button-secondary"
          type="button"
          disabled={disabled}
          onClick={() => inputRef.current?.click()}
        >
          Choose photos
        </button>
        <input
          ref={inputRef}
          className="hidden-file-input"
          type="file"
          accept="image/jpeg,image/png,.jpg,.jpeg,.png"
          multiple
          disabled={disabled}
          aria-label="Choose enforcement photos"
          onChange={(event) => acceptFiles(event.target.files)}
        />
      </div>

      <div className="file-guidance" aria-label="Photo limits">
        {maxFileBytes ? <span>{formatBytes(maxFileBytes)} each</span> : null}
        {maxAggregateBytes ? <span>{formatBytes(maxAggregateBytes)} total</span> : null}
      </div>

      {photos.length > 0 ? (
        <div className="photo-area">
          <div className="photo-summary">
            <p aria-live="polite">
              <strong>{photos.length}</strong> {photos.length === 1 ? 'photo' : 'photos'} ·{' '}
              {formatBytes(totalBytes)}
            </p>
            <button className="text-button" type="button" disabled={disabled} onClick={onClear}>
              Replace all
            </button>
          </div>
          <ul className="photo-grid" aria-label="Selected photos" tabIndex={0}>
            {photos.map((photo, index) => (
              <li key={photo.id} className="photo-card">
                <img src={photo.previewUrl} alt={`Selected photo ${index + 1}: ${photo.file.name}`} />
                <div className="photo-meta">
                  <span title={photo.file.name}>{photo.file.name}</span>
                  <button
                    type="button"
                    className="remove-button"
                    disabled={disabled}
                    onClick={() => onRemove(photo.id)}
                    aria-label={`Remove ${photo.file.name}`}
                  >
                    ×
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
