import { useMemo, useState } from 'react'
import type { EvaluateResponse, FormField } from '../../types'

const LEVELS = ['good', 'moderate', 'poor'] as const
type Level = (typeof LEVELS)[number]

type Props = {
  overallField: FormField | undefined
  evaluate: EvaluateResponse | null
  initial: string | null
  onBack: () => void
  onContinue: (overall: Level) => void
}

function levelIndex(level: string): number {
  return LEVELS.indexOf(level as Level)
}

export function OverallStep({
  overallField,
  evaluate,
  initial,
  onBack,
  onContinue,
}: Props) {
  const [picked, setPicked] = useState<Level | null>(
    initial && LEVELS.includes(initial as Level) ? (initial as Level) : null,
  )
  const [revealed, setRevealed] = useState(Boolean(initial))

  const suggested = (evaluate?.overall_suggested ?? 'moderate') as Level
  const mismatch = useMemo(() => {
    if (!picked) return null
    return Math.abs(levelIndex(picked) - levelIndex(suggested))
  }, [picked, suggested])

  const labels = overallField?.value_labels ?? {
    good: 'Good',
    moderate: 'Moderate',
    poor: 'Poor',
  }

  return (
    <section className="space-y-4" aria-labelledby="overall-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Overall rating</p>
        <h1 id="overall-title" className="text-2xl font-bold text-brand-900">
          {overallField?.question ?? 'Overall ecosystem health'}
        </h1>
        <p className="text-slate-600">
          {overallField?.help ??
            'Choose your rating before seeing the advisory comparison.'}
        </p>
      </header>

      <div className="flex flex-col gap-2" role="radiogroup" aria-label="Overall rating">
        {LEVELS.map((level) => (
          <button
            key={level}
            type="button"
            onClick={() => {
              setPicked(level)
              setRevealed(true)
            }}
            className={[
              'min-h-touch rounded-xl border px-4 text-left text-base font-semibold',
              picked === level
                ? 'border-brand-700 bg-brand-50 ring-2 ring-brand-500'
                : 'border-slate-300 bg-white',
            ].join(' ')}
            aria-pressed={picked === level}
          >
            {labels[level] ?? level}
          </button>
        ))}
      </div>

      {revealed && picked && (
        <div className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="font-semibold text-brand-900">Advisory comparison</h2>
          <p className="text-sm text-slate-700">
            You chose <strong>{labels[picked]}</strong>. Based on{' '}
            {evaluate?.overall_pressure_count ?? '—'} pressure signals, the
            rule-based advisory is <strong>{labels[suggested] ?? suggested}</strong>.
          </p>
          {evaluate?.risk?.ecosystem?.reasons?.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
              {evaluate.risk.ecosystem.reasons.slice(0, 6).map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          ) : null}
          {mismatch !== null && mismatch >= 2 && (
            <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950" role="status">
              Your rating differs by two levels from the advisory. This record
              will be reviewed by an expert.
            </p>
          )}
          <p className="text-xs text-slate-500">
            {evaluate?.risk?.disclaimer ??
              'Indicative only, not a safety certification'}
          </p>
        </div>
      )}

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
          disabled={!picked}
          onClick={() => picked && onContinue(picked)}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white disabled:opacity-50"
        >
          Continue to feelings
        </button>
      </div>
    </section>
  )
}
