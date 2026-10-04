import { useId, useRef, useState } from 'react'
import { resizeImageToJpeg } from '../../lib/resizeImage'
import type { FormField, PhotoRole, PhotoSlot } from '../../types'

const ROLES: PhotoRole[] = ['upstream', 'downstream', 'context', 'biodiversity']

const PHOTO_FIELD_IDS: Record<PhotoRole, string> = {
  upstream: 'photo_upstream',
  downstream: 'photo_downstream',
  context: 'photo_context',
  biodiversity: 'photo_biodiversity',
}

type Props = {
  mediaFields: FormField[]
  photos: Partial<Record<PhotoRole, PhotoSlot>>
  facingDownstream: boolean | null
  onPhoto: (role: PhotoRole, slot: PhotoSlot | null) => void
  onFacingChange: (value: boolean) => void
  onBack: () => void
  onContinue: () => void
}

export function PhotosStep({
  mediaFields,
  photos,
  facingDownstream,
  onPhoto,
  onFacingChange,
  onBack,
  onContinue,
}: Props) {
  const [busyRole, setBusyRole] = useState<PhotoRole | null>(null)
  const [error, setError] = useState<string | null>(null)
  const facingId = useId()

  const fieldById = Object.fromEntries(mediaFields.map((f) => [f.id, f]))

  const filled = ROLES.filter((r) => photos[r]).length
  const canContinue = filled >= 1 && facingDownstream !== null

  async function handleFile(role: PhotoRole, file: File | undefined) {
    if (!file) return
    setBusyRole(role)
    setError(null)
    try {
      const blob = await resizeImageToJpeg(file)
      const previewUrl = URL.createObjectURL(blob)
      const existing = photos[role]
      if (existing) URL.revokeObjectURL(existing.previewUrl)
      onPhoto(role, { role, blob, previewUrl })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not process photo')
    } finally {
      setBusyRole(null)
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="photos-step-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Step 2 of 3</p>
        <h1 id="photos-step-title" className="text-2xl font-bold text-brand-900">
          Stream photos
        </h1>
        <p className="text-slate-600">
          Photos are resized on your phone and saved without location tags from
          the camera (EXIF stripped).
        </p>
      </header>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      <ul className="space-y-3">
        {ROLES.map((role) => {
          const field = fieldById[PHOTO_FIELD_IDS[role]]
          return (
            <PhotoSlotCard
              key={role}
              role={role}
              question={field?.question ?? role}
              help={field?.help ?? ''}
              slot={photos[role]}
              busy={busyRole === role}
              onPick={(file) => void handleFile(role, file)}
              onClear={() => {
                const existing = photos[role]
                if (existing) URL.revokeObjectURL(existing.previewUrl)
                onPhoto(role, null)
              }}
            />
          )
        })}
      </ul>

      <fieldset className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <legend className="px-1 text-base font-semibold text-brand-900">
          Were you facing downstream?
        </legend>
        <p id={`${facingId}-help`} className="text-sm text-slate-600">
          Left and right bank answers are mapped only if you faced downstream.
        </p>
        <div className="flex gap-2 pt-1" role="radiogroup" aria-describedby={`${facingId}-help`}>
          <button
            type="button"
            className={[
              'min-h-touch flex-1 rounded-xl border text-base font-semibold',
              facingDownstream === true
                ? 'border-brand-700 bg-brand-50 text-brand-900'
                : 'border-slate-300 bg-white',
            ].join(' ')}
            aria-pressed={facingDownstream === true}
            onClick={() => onFacingChange(true)}
          >
            Yes
          </button>
          <button
            type="button"
            className={[
              'min-h-touch flex-1 rounded-xl border text-base font-semibold',
              facingDownstream === false
                ? 'border-brand-700 bg-brand-50 text-brand-900'
                : 'border-slate-300 bg-white',
            ].join(' ')}
            aria-pressed={facingDownstream === false}
            onClick={() => onFacingChange(false)}
          >
            No / not sure
          </button>
        </div>
      </fieldset>

      <p className="text-sm text-slate-600">
        {filled} of {ROLES.length} photos ready. At least one photo is required.
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onBack}
          className="min-h-touch flex-1 rounded-xl border border-slate-300 font-semibold"
        >
          Back
        </button>
        <button
          type="button"
          disabled={!canContinue}
          onClick={onContinue}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white disabled:opacity-50"
        >
          Continue to analyze
        </button>
      </div>
    </section>
  )
}

function PhotoSlotCard({
  role,
  question,
  help,
  slot,
  busy,
  onPick,
  onClear,
}: {
  role: PhotoRole
  question: string
  help: string
  slot: PhotoSlot | undefined
  busy: boolean
  onPick: (file: File | undefined) => void
  onClear: () => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const inputId = useId()

  return (
    <li className="rounded-xl border border-slate-200 bg-white p-3">
      <div className="mb-2 space-y-0.5">
        <h2 className="font-semibold text-brand-900">{question}</h2>
        {help && <p className="text-sm text-slate-600">{help}</p>}
      </div>
      {slot ? (
        <div className="space-y-2">
          <img
            src={slot.previewUrl}
            alt={`${role} preview`}
            className="max-h-48 w-full rounded-lg object-cover"
          />
          <div className="flex gap-2">
            <button
              type="button"
              className="min-h-touch flex-1 rounded-lg border border-slate-300 font-medium"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
            >
              Replace
            </button>
            <button
              type="button"
              className="min-h-touch flex-1 rounded-lg border border-red-200 text-red-800 font-medium"
              onClick={onClear}
              disabled={busy}
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          className="flex min-h-[88px] w-full items-center justify-center rounded-lg border border-dashed border-brand-500 text-base font-semibold text-brand-700"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
        >
          {busy ? 'Processing…' : 'Take or choose photo'}
        </button>
      )}
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0]
          onPick(file)
          e.target.value = ''
        }}
      />
    </li>
  )
}
