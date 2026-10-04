import { useEffect, useRef, useState } from 'react'
import { evaluateObservation } from '../../api/client'
import { GROUP_TITLES, shouldApplyAiMarginSuggestion } from '../../lib/margins'
import type {
  AnalyzeResponse,
  EvaluateResponse,
  FieldSource,
  FieldSuggestion,
  FormField,
  Site,
  ValidationFlag,
} from '../../types'

type Props = {
  schemaFields: FormField[]
  site: Site
  facingDownstream: boolean
  userLat: number | null
  userLon: number | null
  analyze: AnalyzeResponse | null
  answers: Record<string, unknown>
  fieldSources: Record<string, FieldSource>
  onAnswersChange: (
    answers: Record<string, unknown>,
    sources: Record<string, FieldSource>,
  ) => void
  onEvaluate: (result: EvaluateResponse | null) => void
  onBack: () => void
  onContinue: () => void
}

const REVIEW_GROUPS = ['questions_1', 'questions_2', 'questions_3'] as const

function reviewFields(schemaFields: FormField[]): FormField[] {
  return schemaFields.filter(
    (f) =>
      REVIEW_GROUPS.includes(f.group as (typeof REVIEW_GROUPS)[number]) &&
      f.value_type !== 'feelings' &&
      f.id !== 'overall_assessment',
  )
}

function labelFor(field: FormField, value: unknown): string {
  if (value == null || value === '') return '—'
  const key = String(value)
  return field.value_labels?.[key] ?? key
}

export function ReviewStep({
  schemaFields,
  site,
  facingDownstream,
  userLat,
  userLon,
  analyze,
  answers,
  fieldSources,
  onAnswersChange,
  onEvaluate,
  onBack,
  onContinue,
}: Props) {
  const fields = reviewFields(schemaFields)
  const suggestions = analyze?.status === 'ok' ? analyze.suggestions : {}
  const suggestionsKey = JSON.stringify(suggestions)
  const [flags, setFlags] = useState<ValidationFlag[]>([])
  const [evalError, setEvalError] = useState<string | null>(null)
  const [evalBusy, setEvalBusy] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const onEvaluateRef = useRef(onEvaluate)

  useEffect(() => {
    onEvaluateRef.current = onEvaluate
  }, [onEvaluate])

  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(() => {
      setEvalBusy(true)
      const parsedSuggestions =
        analyze?.status === 'ok' ? analyze.suggestions : {}
      void evaluateObservation({
        site_id: site.id,
        user_lat: userLat,
        user_lon: userLon,
        facing_downstream: facingDownstream,
        answers,
        field_sources: fieldSources,
        ai_suggestions: parsedSuggestions,
        include_context: false,
      })
        .then((result) => {
          if (cancelled) return
          setFlags(result.flags)
          onEvaluateRef.current(result)
          setEvalError(null)
        })
        .catch((err: unknown) => {
          if (cancelled) return
          setEvalError(err instanceof Error ? err.message : 'Evaluate failed')
        })
        .finally(() => {
          if (!cancelled) setEvalBusy(false)
        })
    }, 400)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [
    answers,
    fieldSources,
    site.id,
    facingDownstream,
    userLat,
    userLon,
    suggestionsKey,
    analyze,
  ])

  function updateField(fieldId: string, value: unknown, source: FieldSource) {
    const nextAnswers = { ...answers, [fieldId]: value }
    const nextSources = { ...fieldSources, [fieldId]: source }
    if (value === undefined) {
      delete nextAnswers[fieldId]
      nextSources[fieldId] = 'unanswered'
    }
    onAnswersChange(nextAnswers, nextSources)
    setEditingId(null)
  }

  const grouped = REVIEW_GROUPS.map((group) => ({
    group,
    title: GROUP_TITLES[group] ?? group,
    items: fields.filter((f) => f.group === group),
  })).filter((g) => g.items.length > 0)

  const aiUnavailable = analyze?.status === 'ai_unavailable'

  return (
    <section className="space-y-4" aria-labelledby="review-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Review answers</p>
        <h1 id="review-title" className="text-2xl font-bold text-brand-900">
          Check each suggestion
        </h1>
        <p className="text-slate-600">
          Accept, edit, or mark not sure. AI never saves a final answer without
          you.
        </p>
      </header>

      {aiUnavailable && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
          AI is unavailable, please answer manually.
        </p>
      )}

      {!facingDownstream && (
        <p className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700">
          You were not facing downstream, so left/right margin AI suggestions
          are not applied. Please answer those yourself.
        </p>
      )}

      {analyze?.upstream_vs_downstream && (
        <p className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
          Upstream vs downstream: {analyze.upstream_vs_downstream}
        </p>
      )}

      <div className="space-y-2" aria-live="polite">
        {evalBusy && (
          <p className="text-sm text-slate-500">Checking consistency…</p>
        )}
        {evalError && (
          <p className="text-sm text-red-700" role="alert">
            {evalError}
          </p>
        )}
        {flags.map((flag) => (
          <p
            key={flag.code + flag.fields.join(',')}
            className={[
              'rounded-lg px-3 py-2 text-sm',
              flag.severity === 'error'
                ? 'bg-red-50 text-red-900'
                : flag.severity === 'warning'
                  ? 'bg-amber-50 text-amber-950'
                  : 'bg-slate-100 text-slate-800',
            ].join(' ')}
          >
            {flag.message}
          </p>
        ))}
      </div>

      {grouped.map(({ group, title, items }) => (
        <div key={group} className="space-y-3">
          <h2 className="text-lg font-semibold text-brand-900">{title}</h2>
          {items.map((field) => (
            <FieldCard
              key={field.id}
              field={field}
              value={answers[field.id]}
              source={fieldSources[field.id] ?? 'unanswered'}
              suggestion={
                shouldApplyAiMarginSuggestion(field.id, facingDownstream)
                  ? suggestions[field.id]
                  : undefined
              }
              editing={editingId === field.id}
              relatedFlags={flags.filter((f) => f.fields.includes(field.id))}
              onAccept={() => {
                const s = suggestions[field.id]
                if (!s) return
                updateField(field.id, s.value, 'ai_accepted')
              }}
              onNotSure={() => updateField(field.id, 'not_sure', 'human')}
              onStartEdit={() => setEditingId(field.id)}
              onCancelEdit={() => setEditingId(null)}
              onPick={(val) => {
                const hadAi = Boolean(suggestions[field.id])
                const source: FieldSource =
                  field.ai_role === 'human_only'
                    ? 'human'
                    : hadAi
                      ? 'ai_edited'
                      : 'human'
                updateField(field.id, val, source)
              }}
              onClear={() => updateField(field.id, undefined, 'unanswered')}
            />
          ))}
        </div>
      ))}

      <div className="flex gap-2 pt-2">
        <button
          type="button"
          onClick={onBack}
          className="min-h-touch flex-1 rounded-xl border border-slate-300 font-semibold"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onContinue}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white"
        >
          Continue to overall rating
        </button>
      </div>
    </section>
  )
}

function FieldCard({
  field,
  value,
  source,
  suggestion,
  editing,
  relatedFlags,
  onAccept,
  onNotSure,
  onStartEdit,
  onCancelEdit,
  onPick,
  onClear,
}: {
  field: FormField
  value: unknown
  source: FieldSource
  suggestion?: FieldSuggestion
  editing: boolean
  relatedFlags: ValidationFlag[]
  onAccept: () => void
  onNotSure: () => void
  onStartEdit: () => void
  onCancelEdit: () => void
  onPick: (value: string | number) => void
  onClear: () => void
}) {
  const showAi = Boolean(suggestion) && field.ai_role !== 'human_only'
  const answered = value !== undefined && value !== null && value !== ''

  return (
    <article className="space-y-2 rounded-2xl border border-slate-200/80 bg-white/80 p-4 shadow-[0_12px_24px_rgba(15,76,92,0.06)]">
      <header className="space-y-1">
        <h3 className="font-semibold text-brand-900">{field.question}</h3>
        <p className="text-sm text-slate-600">{field.help}</p>
        {field.pending_note && (
          <p className="text-xs text-amber-800">{field.pending_note}</p>
        )}
      </header>

      {showAi && suggestion && (
        <div className="rounded-2xl bg-brand-50/80 px-3 py-2 text-sm shadow-[0_6px_18px_rgba(15,76,92,0.05)]">
          <p className="font-medium text-brand-800">
            AI suggests · {Math.round(suggestion.confidence * 100)}%
          </p>
          <p className="text-brand-900">{labelFor(field, suggestion.value)}</p>
          <p className="text-slate-600">{suggestion.reason}</p>
        </div>
      )}

      {answered && !editing && (
        <p className="text-sm">
          <span className="font-medium">Your answer:</span>{' '}
          {labelFor(field, value)}{' '}
          <span className="rounded-full border border-slate-200 bg-slate-100 px-2 py-0.5 text-[11px] font-medium">
            {source.replace('_', ' ')}
          </span>
        </p>
      )}

      {relatedFlags.map((f) => (
        <p key={f.code} className="text-sm text-amber-900">
          {f.message}
        </p>
      ))}

      {editing || field.ai_role === 'human_only' || !showAi ? (
        <FieldEditor
          field={field}
          value={value}
          onPick={onPick}
          onCancel={onCancelEdit}
          showCancel={editing}
        />
      ) : (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onAccept}
            className="min-h-touch flex-1 rounded-xl bg-brand-700 px-3 text-sm font-semibold text-white"
          >
            Accept
          </button>
          <button
            type="button"
            onClick={onStartEdit}
            className="min-h-touch flex-1 rounded-lg border border-slate-300 px-3 text-sm font-semibold"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={onNotSure}
            className="min-h-touch flex-1 rounded-lg border border-slate-300 px-3 text-sm font-semibold"
          >
            Not sure
          </button>
          {answered && (
            <button
              type="button"
              onClick={onClear}
              className="min-h-touch w-full rounded-lg text-sm text-slate-600 underline"
            >
              Clear answer
            </button>
          )}
        </div>
      )}
    </article>
  )
}

function FieldEditor({
  field,
  value,
  onPick,
  onCancel,
  showCancel,
}: {
  field: FormField
  value: unknown
  onPick: (value: string | number) => void
  onCancel: () => void
  showCancel: boolean
}) {
  if (field.value_type === 'number') {
    return (
      <div className="space-y-2">
        <label className="block space-y-1">
          <span className="sr-only">{field.question}</span>
          <input
            type="number"
            inputMode="decimal"
            className="min-h-touch w-full rounded-lg border border-slate-300 px-3"
            value={typeof value === 'number' ? value : ''}
            onChange={(e) => {
              const raw = e.target.value
              if (raw === '') return
              onPick(Number(raw))
            }}
            placeholder="cm (unit to confirm)"
          />
        </label>
        {showCancel && (
          <button type="button" className="text-sm underline" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    )
  }

  if (field.value_type === 'text') {
    return (
      <div className="space-y-2">
        <textarea
          className="min-h-[88px] w-full rounded-lg border border-slate-300 px-3 py-2"
          value={typeof value === 'string' ? value : ''}
          onChange={(e) => onPick(e.target.value)}
          aria-label={field.question}
        />
        {showCancel && (
          <button type="button" className="text-sm underline" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    )
  }

  const options = field.values ?? []
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {options.map((opt) => {
          const selected = value === opt
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onPick(opt)}
              className={[
                'min-h-touch rounded-lg border px-3 text-sm font-medium',
                selected
                  ? 'border-brand-700 bg-brand-50 text-brand-900'
                  : 'border-slate-300',
              ].join(' ')}
              aria-pressed={selected}
            >
              {field.value_labels?.[opt] ?? opt}
            </button>
          )
        })}
      </div>
      {showCancel && (
        <button type="button" className="text-sm underline" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  )
}
