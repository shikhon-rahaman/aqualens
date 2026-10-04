import { useMemo, useState } from 'react'
import { analyzePhotos } from '../../api/client'
import type { AnalyzeResponse, PhotoRole, PhotoSlot, Site } from '../../types'

type Props = {
  site: Site
  facingDownstream: boolean
  photos: Partial<Record<PhotoRole, PhotoSlot>>
  onBack: () => void
  onDone: (result: AnalyzeResponse) => void
}

export function AnalyzeStep({
  site,
  facingDownstream,
  photos,
  onBack,
  onDone,
}: Props) {
  const [progress, setProgress] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)

  const roles = useMemo(
    () =>
      (Object.keys(photos) as PhotoRole[]).filter((role) => photos[role] != null),
    [photos],
  )

  async function runAnalyze() {
    setRunning(true)
    setError(null)
    setProgress('Sending photos to AI…')
    try {
      const blobs: Partial<Record<PhotoRole, Blob>> = {}
      for (const role of roles) {
        const slot = photos[role]
        if (slot) blobs[role] = slot.blob
      }
      setProgress('Waiting for suggestions…')
      const result = await analyzePhotos(blobs)
      onDone(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analyze failed')
      setProgress(null)
    } finally {
      setRunning(false)
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="analyze-step-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Step 3 of 3</p>
        <h1 id="analyze-step-title" className="text-2xl font-bold text-brand-900">
          Analyze with AI
        </h1>
        <p className="text-slate-600">
          AI only suggests answers. You will confirm or edit every field next.
        </p>
      </header>

      <dl className="space-y-2 rounded-xl border border-slate-200 bg-white p-4 text-sm">
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Site</dt>
          <dd className="font-medium text-brand-900 text-right">{site.name}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Facing downstream</dt>
          <dd className="font-medium">{facingDownstream ? 'Yes' : 'No / not sure'}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-slate-500">Photos</dt>
          <dd className="font-medium">{roles.join(', ')}</dd>
        </div>
      </dl>

      {progress && (
        <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-900" aria-live="polite">
          {progress}
        </p>
      )}
      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={running}
          className="min-h-touch flex-1 rounded-xl border border-slate-300 font-semibold disabled:opacity-50"
        >
          Back
        </button>
        <button
          type="button"
          onClick={() => void runAnalyze()}
          disabled={running || roles.length === 0}
          className="min-h-touch flex-[2] rounded-xl bg-brand-700 font-semibold text-white disabled:opacity-50"
        >
          {running ? 'Analyzing…' : 'Analyze with AI'}
        </button>
      </div>

      <button
        type="button"
        disabled={running}
        onClick={() =>
          onDone({
            status: 'ai_unavailable',
            suggestions: {},
            message: 'AI is unavailable, please answer manually.',
          })
        }
        className="min-h-touch w-full rounded-xl border border-slate-300 text-sm font-medium text-slate-700"
      >
        Skip AI and answer manually
      </button>
    </section>
  )
}
