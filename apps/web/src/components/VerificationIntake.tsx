import type { VerificationWorkflow } from '../hooks/useVerificationWorkflow'
import { PhotoPicker } from './PhotoPicker'

interface VerificationIntakeProps {
  workflow: VerificationWorkflow
}

export function VerificationIntake({ workflow }: VerificationIntakeProps) {
  const {
    addPhotos,
    addPhotosRef,
    capabilities,
    clearPhotos,
    isBusy,
    photoError,
    photos,
    removePhoto,
    runVerification,
    sampleBusy,
    useSamplePhotos,
    verification,
  } = workflow

  return (
    <div className="intake-column">
      <div className="intake-card" ref={addPhotosRef}>
        <PhotoPicker
          photos={photos}
          disabled={isBusy}
          maxFileBytes={capabilities.max_file_bytes}
          maxAggregateBytes={capabilities.max_aggregate_bytes}
          sampleBusy={sampleBusy}
          onAdd={addPhotos}
          onUseSample={(sampleId) => void useSamplePhotos(sampleId)}
          onRemove={removePhoto}
          onClear={clearPhotos}
        />
        {photoError ? (
          <p className="error-banner intake-error" role="alert">{photoError}</p>
        ) : null}

        <div className="verify-bar">
          <div>
            <strong>{photos.length ? 'Ready to verify' : 'Add photos to begin'}</strong>
            <span>
              {photos.length
                ? `${photos.length} ${photos.length === 1 ? 'photo' : 'photos'} selected`
                : 'At least one photo is required'}
            </span>
          </div>
          <button
            className="button button-primary"
            type="button"
            onClick={() => void runVerification()}
            disabled={isBusy || !photos.length}
          >
            {verification ? 'Run again' : 'Verify label'}
          </button>
        </div>
      </div>
    </div>
  )
}
