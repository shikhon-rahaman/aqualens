import { useEffect, useState } from 'react'
import {
  fetchExpertQueue,
  fetchObservation,
  expertReviewObservation,
  fetchFormSchema,
} from '../../api/client'
import type { ObservationOut, FormField } from '../../types'

type QueueItem = {
  id: string
  site_name: string | null
  status: string
  needs_expert: boolean
  risk_ecosystem: string | null
  overall_user: string | null
  is_synthetic: boolean
  captured_at: string
}

export function ExpertPage() {
  const [pin, setPin] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<ObservationOut | null>(null)
  const [schema, setSchema] = useState<FormField[]>([])
  const [editing, setEditing] = useState(false)
  const [editAnswers, setEditAnswers] = useState<Record<string, unknown>>({})
  const [reviewing, setReviewing] = useState(false)

  useEffect(() => {
    fetchFormSchema()
      .then((data) => setSchema(data.fields))
      .catch(() => {})
  }, [])

  async function handleAuth() {
    if (!pin.trim()) {
      setError('PIN required')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const data = await fetchExpertQueue(pin)
      setQueue(data.observations)
      setAuthenticated(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  async function loadDetail(id: string) {
    setSelectedId(id)
    setDetail(null)
    setError(null)
    try {
      const obs = await fetchObservation(id)
      setDetail(obs)
      setEditAnswers(obs.answers || {})
      setEditing(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load observation')
    }
  }

  async function handleReview(action: 'approve' | 'correct') {
    if (!selectedId || !detail) return
    setReviewing(true)
    setError(null)
    try {
      await expertReviewObservation(
        selectedId,
        pin,
        action,
        action === 'correct' ? editAnswers : undefined,
        action === 'correct' ? detail.field_sources : undefined,
      )
      // Refresh queue
      const data = await fetchExpertQueue(pin)
      setQueue(data.observations)
      setSelectedId(null)
      setDetail(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review action failed')
    } finally {
      setReviewing(false)
    }
  }

  if (!authenticated) {
    return (
      <div className="space-y-4">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold text-brand-900">Expert review</h1>
          <p className="text-slate-600">Enter PIN to access the review queue.</p>
          <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950">
            ⚠ Demo-only authentication. Real auth is future work.
          </p>
        </header>

        <div className="space-y-2">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Expert PIN</span>
            <input
              type="password"
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void handleAuth()
              }}
              className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
              placeholder="Enter PIN from .env"
            />
          </label>
          {error && (
            <p className="text-sm text-red-700" role="alert">
              {error}
            </p>
          )}
          <button
            type="button"
            onClick={() => void handleAuth()}
            disabled={loading}
            className="min-h-touch w-full rounded-xl bg-brand-700 font-semibold text-white disabled:opacity-50"
          >
            {loading ? 'Authenticating…' : 'Access queue'}
          </button>
        </div>
      </div>
    )
  }

  if (detail) {
    return (
      <DetailView
        observation={detail}
        schema={schema}
        editing={editing}
        editAnswers={editAnswers}
        reviewing={reviewing}
        error={error}
        onBack={() => {
          setSelectedId(null)
          setDetail(null)
          setEditing(false)
        }}
        onStartEdit={() => setEditing(true)}
        onCancelEdit={() => {
          setEditing(false)
          setEditAnswers(detail.answers || {})
        }}
        onFieldChange={(fieldId, value) =>
          setEditAnswers((prev) => ({ ...prev, [fieldId]: value }))
        }
        onApprove={() => void handleReview('approve')}
        onCorrect={() => void handleReview('correct')}
      />
    )
  }

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold text-brand-900">Expert queue</h1>
        <p className="text-slate-600">
          {queue.length} observation{queue.length !== 1 ? 's' : ''} need review
        </p>
      </header>

      {queue.length === 0 ? (
        <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">
          No observations pending review.
        </p>
      ) : (
        <ul className="space-y-2">
          {queue.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                onClick={() => void loadDetail(item.id)}
                className="w-full rounded-xl border border-slate-200 bg-white p-3 text-left hover:border-brand-300"
              >
                <p className="font-semibold text-brand-900">
                  {item.site_name ?? 'Unknown site'}
                </p>
                <p className="text-sm text-slate-600">
                  User rating: {item.overall_user ?? '—'} · AI:{' '}
                  {item.risk_ecosystem ?? '—'}
                </p>
                <p className="text-xs text-slate-500">
                  {new Date(item.captured_at).toLocaleString()}
                  {item.is_synthetic && <> · Demo data</>}
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="button"
        onClick={() => {
          setAuthenticated(false)
          setPin('')
          setQueue([])
        }}
        className="text-sm text-slate-600 underline"
      >
        Sign out
      </button>
    </div>
  )
}

function DetailView({
  observation,
  schema,
  editing,
  editAnswers,
  reviewing,
  error,
  onBack,
  onStartEdit,
  onCancelEdit,
  onFieldChange,
  onApprove,
  onCorrect,
}: {
  observation: ObservationOut
  schema: FormField[]
  editing: boolean
  editAnswers: Record<string, unknown>
  reviewing: boolean
  error: string | null
  onBack: () => void
  onStartEdit: () => void
  onCancelEdit: () => void
  onFieldChange: (fieldId: string, value: unknown) => void
  onApprove: () => void
  onCorrect: () => void
}) {
  const answerFields = schema.filter(
    (f) =>
      f.value_type === 'choice' || f.value_type === 'number' || f.value_type === 'text',
  )

  const photoRoles = ['upstream', 'downstream', 'context', 'biodiversity'] as const

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-brand-600 underline"
        >
          ← Back to queue
        </button>
        <h1 className="text-2xl font-bold text-brand-900">Review observation</h1>
        <p className="text-slate-600">
          {observation.site_name ?? 'Unknown site'} · {observation.status}
        </p>
      </header>

      {observation.photos && Object.keys(observation.photos).length > 0 && (
        <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-brand-900">Photos</h2>
          <div className="grid grid-cols-2 gap-2">
            {photoRoles.map((role) => {
              const url = observation.photos[role]
              if (!url) return null
              return (
                <div key={role} className="space-y-1">
                  <img
                    src={url}
                    alt={role}
                    className="aspect-video w-full rounded border border-slate-200 object-cover"
                  />
                  <p className="text-xs capitalize text-slate-600">{role}</p>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {observation.flags && observation.flags.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-semibold text-brand-900">Flags</h2>
          {observation.flags.map((f: any) => (
            <p
              key={f.code}
              className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950"
            >
              {f.message}
            </p>
          ))}
        </section>
      )}

      <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-brand-900">Answers</h2>
          {!editing && (
            <button
              type="button"
              onClick={onStartEdit}
              className="text-sm font-medium text-brand-600 underline"
            >
              Edit
            </button>
          )}
        </div>
        <ul className="space-y-2">
          {answerFields.map((field) => {
            const value = editing ? editAnswers[field.id] : observation.answers[field.id]
            const source = observation.field_sources[field.id]
            return (
              <li
                key={field.id}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              >
                <p className="font-medium text-brand-900">{field.question}</p>
                {editing ? (
                  <FieldInput
                    field={field}
                    value={value}
                    onChange={(v) => onFieldChange(field.id, v)}
                  />
                ) : (
                  <p className="text-slate-700">
                    {displayValue(field, value)}{' '}
                    {source && (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs">
                        {source.replace('_', ' ')}
                      </span>
                    )}
                  </p>
                )}
              </li>
            )
          })}
        </ul>
        {editing && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancelEdit}
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onCorrect}
              disabled={reviewing}
              className="flex-1 rounded-lg bg-brand-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              {reviewing ? 'Saving…' : 'Save corrections'}
            </button>
          </div>
        )}
      </section>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      {!editing && (
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onApprove}
            disabled={reviewing}
            className="flex-1 rounded-xl bg-green-700 font-semibold text-white disabled:opacity-50"
          >
            {reviewing ? 'Processing…' : 'Approve'}
          </button>
          <button
            type="button"
            onClick={onStartEdit}
            disabled={reviewing}
            className="flex-1 rounded-xl border border-slate-300 font-semibold disabled:opacity-50"
          >
            Correct
          </button>
        </div>
      )}
    </div>
  )
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: FormField
  value: unknown
  onChange: (value: unknown) => void
}) {
  if (field.value_type === 'number') {
    return (
      <input
        type="number"
        inputMode="decimal"
        value={typeof value === 'number' ? value : ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="mt-1 w-full rounded border border-slate-300 px-2 py-1 text-sm"
      />
    )
  }

  if (field.value_type === 'text') {
    return (
      <textarea
        value={typeof value === 'string' ? value : ''}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 min-h-[60px] w-full rounded border border-slate-300 px-2 py-1 text-sm"
      />
    )
  }

  const options = field.values ?? []
  return (
    <div className="mt-1 flex flex-wrap gap-1">
      {options.map((opt) => (
        <button
          key={opt}
          type="button"
          onClick={() => onChange(opt)}
          className={[
            'rounded border px-2 py-1 text-sm',
            value === opt
              ? 'border-brand-700 bg-brand-50 text-brand-900'
              : 'border-slate-300',
          ].join(' ')}
        >
          {field.value_labels?.[opt] ?? opt}
        </button>
      ))}
    </div>
  )
}

function displayValue(field: FormField, value: unknown): string {
  if (value == null || value === '') return '—'
  const key = String(value)
  return field.value_labels?.[key] ?? key
}
