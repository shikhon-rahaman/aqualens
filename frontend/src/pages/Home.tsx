import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchHealth, type HealthResponse } from '../api/client'

type LoadState =
  | { status: 'loading' }
  | { status: 'ok'; data: HealthResponse }
  | { status: 'error'; message: string }

export function HomePage() {
  const [health, setHealth] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    fetchHealth()
      .then((data) => {
        if (!cancelled) setHealth({ status: 'ok', data })
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setHealth({
            status: 'error',
            message: err instanceof Error ? err.message : 'Could not reach API',
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-brand-500">
          OneAquaHealth companion
        </p>
        <h1 className="text-3xl font-bold text-brand-900">AquaLens</h1>
        <p className="text-base text-slate-600">
          AI suggests stream answers. You confirm. Validation and FHIR keep the
          record trustworthy.
        </p>
      </header>

      <section
        className="glass-card p-5"
        aria-live="polite"
      >
        <h2 className="mb-2 text-lg font-semibold text-brand-900">API health</h2>
        {health.status === 'loading' && (
          <p className="text-slate-600">Checking backend…</p>
        )}
        {health.status === 'error' && (
          <p className="text-red-700" role="alert">
            {health.message}. Start the API on port 8000, then refresh.
          </p>
        )}
        {health.status === 'ok' && (
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Status</dt>
              <dd className="font-medium text-brand-700">{health.data.status}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Database</dt>
              <dd className="font-medium">{health.data.db}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">AI chain</dt>
              <dd className="font-medium">{health.data.ai_chain.join(' → ')}</dd>
            </div>
          </dl>
        )}
      </section>

      <Link
        to="/observe"
        className="inline-flex min-h-touch w-full items-center justify-center rounded-2xl bg-brand-700 px-4 text-base font-semibold text-white"
      >
        Start an observation
      </Link>
    </div>
  )
}
