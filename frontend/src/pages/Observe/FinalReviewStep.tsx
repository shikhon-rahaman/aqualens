import { useState } from 'react'
import { createObservation } from '../../api/client'
import { SOURCE_LABELS } from '../../lib/margins'
import type {
  AnalyzeResponse,
  FeelingsAnswers,
  FieldSource,
  FormField,
  PhotoRole,
  PhotoSlot,
  Site,
} from '../../types'

type Props = {
  schemaFields: FormField[]
  site: Site
  facingDownstream: boolean
  userLat: number | null
  userLon: number | null
  answers: Record<string, unknown>
  fieldSources: Record<string, FieldSource>
  feelings: FeelingsAnswers
  analyze: AnalyzeResponse | null
  photos: Partial<Record<PhotoRole, PhotoSlot>>
  onBack: () => void
  onSaved: (observationId: string) => void
}

function displayValue(field: FormField | undefined, value: unknown): string {
  if (value == null || value === '') return '—'
  if (field?.value_type === 'feelings') return '(see feelings)'
  if (typeof value === 'object') return JSON.stringify(value)
  const key = String(value)
  return field?.value_labels?.[key] ?? key
}

export function FinalReviewStep({
  schemaFields,
  site,
  facingDownstream,
  userLat,
  userLon,
  answers,
  fieldSources,
  feelings,
  analyze,
  photos,
  onBack,
  onSaved,
}: Props) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const answerFields = schemaFields.filter(
    (f) =>
      f.value_type === 'choice' ||
      f.value_type === 'number' ||
      f.value_type === 'text',
  )

  async function handleSave() {
    setSaving(true)
    setError(null)
    try {
      const photoBlobs: Partial<Record<PhotoRole, Blob>> = {}
      for (const role of Object.keys(photos) as PhotoRole[]) {
        const slot = photos[role]
        if (slot) photoBlobs[role] = slot.blob
      }
      const overall =
        typeof answers.overall_assessment === 'string'
          ? answers.overall_assessment
          : null
      const created = await createObservation({
        site_id: site.id,
        facing_downstream: facingDownstream,
        user_lat: userLat,
        user_lon: userLon,
        answers,
        field_sources: fieldSources,
        ai_suggestions: analyze?.suggestions ?? {},
        feelings,
        overall_user: overall,
        photos: photoBlobs,
      })
      onSaved(created.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="final-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Final review</p>
        <h1 id="final-title" className="text-2xl font-bold text-brand-900">
          Ready to save?
        </h1>
        <p className="text-slate-600">
          Check sources, then save. Photos and feelings stay off the public FHIR
          export.
        </p>
      </header>

      <dl className="space-y-1 rounded-xl border border-slate-200 bg-white p-4 text-sm">
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">Site</dt>
          <dd className="font-medium text-right">{site.name}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">Facing downstream</dt>
          <dd className="font-medium">{facingDownstream ? 'Yes' : 'No'}</dd>
        </div>
        <div className="flex justify-between gap-2">
          <dt className="text-slate-500">Photos</dt>
          <dd className="font-medium">
            {Object.keys(photos).length || 'none'}
          </dd>
        </div>
      </dl>

      <ul className="space-y-2">
        {answerFields.map((field) => {
          const value = answers[field.id]
          if (value === undefined || value === null || value === '') return null
          const source = fieldSources[field.id] ?? 'human'
          return (
            <li
              key={field.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-brand-900">{field.question}</p>
                <p className="text-slate-700">{displayValue(field, value)}</p>
              </div>
              <span className="shrink-0 rounded bg-slate-100 px-2 py-1 text-xs font-medium">
                {SOURCE_LABELS[source] ?? source}
              </span>
            </li>
          )
        })}
      </ul>

      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
        <h2 className="mb-2 font-semibold text-brand-900">Feelings</h2>
        <ul className="grid grid-cols-2 gap-2">
          {(Object.keys(feelings) as (keyof FeelingsAnswers)[]).map((key) => (
            <li key={key} className="capitalize">
              {key}:{' '}
              {feelings[key].na ? 'N/A' : feelings[key].value}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-slate-500">Source: entered by you</p>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={saving}
          className="min-h-touch flex-1 rounded-xl border border-slate-300 font-semibold disabled:opacity-50"
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => void handleSave()}
          disabled={saving}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save observation'}
        </button>
      </div>
    </section>
  )
}
