import type { FeelingEntry, FeelingsAnswers, FormField } from '../../types'

const KEYS = ['joy', 'serenity', 'anger', 'fear'] as const

type Props = {
  feelingsField: FormField | undefined
  value: FeelingsAnswers
  onChange: (next: FeelingsAnswers) => void
  onBack: () => void
  onContinue: () => void
}

export function FeelingsStep({
  feelingsField,
  value,
  onChange,
  onBack,
  onContinue,
}: Props) {
  function setKey(key: (typeof KEYS)[number], entry: FeelingEntry) {
    onChange({ ...value, [key]: entry })
  }

  return (
    <section className="space-y-4" aria-labelledby="feelings-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Feelings</p>
        <h1 id="feelings-title" className="text-2xl font-bold text-brand-900">
          {feelingsField?.question ?? 'How does this place make you feel?'}
        </h1>
        <p className="text-slate-600">
          {feelingsField?.help ??
            'Rate each feeling from 1 to 5, or mark Not applicable. No AI on this step.'}
        </p>
      </header>

      <ul className="space-y-4">
        {KEYS.map((key) => {
          const entry = value[key]
          return (
            <li
              key={key}
              className="space-y-2 rounded-xl border border-slate-200 bg-white p-4"
            >
              <div className="flex items-center justify-between gap-2">
                <label
                  htmlFor={`feeling-${key}`}
                  className="text-base font-semibold capitalize text-brand-900"
                >
                  {key}
                </label>
                <label className="flex min-h-touch items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={entry.na}
                    onChange={(e) =>
                      setKey(key, {
                        value: e.target.checked ? null : 3,
                        na: e.target.checked,
                      })
                    }
                  />
                  Not applicable
                </label>
              </div>
              <input
                id={`feeling-${key}`}
                type="range"
                min={1}
                max={5}
                step={1}
                disabled={entry.na}
                value={entry.na ? 3 : (entry.value ?? 3)}
                onChange={(e) =>
                  setKey(key, { value: Number(e.target.value), na: false })
                }
                className="w-full"
                aria-valuetext={
                  entry.na ? 'Not applicable' : String(entry.value ?? 3)
                }
              />
              <p className="text-sm text-slate-600">
                {entry.na ? 'Not applicable' : `Score: ${entry.value ?? 3}`}
              </p>
            </li>
          )
        })}
      </ul>

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
          onClick={onContinue}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white"
        >
          Continue to final review
        </button>
      </div>
    </section>
  )
}
