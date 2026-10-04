import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  fetchObservation,
  fetchObservationFhir,
  sendObservationToFhir,
} from '../api/client'
import type { ObservationOut } from '../types'
import { SiteFeelingsChart } from '../components/SiteFeelingsChart'

export function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const [obs, setObs] = useState<ObservationOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [fhirData, setFhirData] = useState<any>(null)
  const [fhirError, setFhirError] = useState<string | null>(null)
  const [showFhir, setShowFhir] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<any>(null)

  useEffect(() => {
    if (!id) return
    let cancelled = false
    fetchObservation(id)
      .then((data) => {
        if (!cancelled) setObs(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load result')
        }
      })
    return () => {
      cancelled = true
    }
  }, [id])

  async function loadFhir() {
    if (!id) return
    setFhirError(null)
    try {
      const data = await fetchObservationFhir(id)
      setFhirData(data)
      setShowFhir(true)
    } catch (err) {
      setFhirError(err instanceof Error ? err.message : 'Could not load FHIR')
    }
  }

  async function handleSendFhir() {
    if (!id) return
    setSending(true)
    setSendResult(null)
    try {
      const result = await sendObservationToFhir(id)
      setSendResult(result)
      if (result.ok) {
        const updated = await fetchObservation(id)
        setObs(updated)
      }
    } catch (err) {
      setSendResult({
        ok: false,
        error: err instanceof Error ? err.message : 'Send failed',
      })
    } finally {
      setSending(false)
    }
  }

  if (error) {
    return (
      <p className="rounded-lg bg-red-50 px-3 py-2 text-red-800" role="alert">
        {error}
      </p>
    )
  }

  if (!obs) {
    return <p className="text-slate-600">Loading result…</p>
  }

  const reasons = obs.risk_reasons as
    | { contact?: string[]; ecosystem?: string[]; disclaimer?: string }
    | null

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Saved</p>
        <h1 className="text-2xl font-bold text-brand-900">Observation result</h1>
        <p className="text-slate-600">
          {obs.site_name ?? 'Site'} · status {obs.status}
          {obs.needs_expert ? ' · needs expert review' : ''}
        </p>
      </header>

      <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold text-brand-900">Risk notes</h2>
        <div className="space-y-3">
          <div>
            <p className="text-sm">
              Contact safety:{' '}
              <strong className="capitalize">{obs.risk_contact ?? '—'}</strong>
            </p>
            {reasons?.contact?.length ? (
              <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
                {reasons.contact.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
          </div>
          <div>
            <p className="text-sm">
              Ecosystem pressure:{' '}
              <strong className="capitalize">{obs.risk_ecosystem ?? '—'}</strong>
            </p>
            {reasons?.ecosystem?.length ? (
              <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm text-slate-600">
                {reasons.ecosystem.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            ) : null}
          </div>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          {typeof reasons?.disclaimer === 'string'
            ? reasons.disclaimer
            : 'Indicative only, not a safety certification'}
        </p>
      </section>

      <section className="space-y-2 rounded-2xl border border-slate-200/80 bg-white/80 p-5 text-sm shadow-[0_12px_26px_rgba(15,76,92,0.07)]">
        <h2 className="font-semibold text-brand-900">Your rating</h2>
        <p>
          You: <strong className="capitalize">{obs.overall_user ?? '—'}</strong>
          {' · '}
          Advisory:{' '}
          <strong className="capitalize">{obs.overall_suggested ?? '—'}</strong>
        </p>
      </section>

      {obs.flags && obs.flags.length > 0 && (
        <section className="space-y-2">
          <h2 className="font-semibold text-brand-900">Flags</h2>
          {obs.flags.map((f) => (
            <p
              key={f.code}
              className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950"
            >
              {f.message}
            </p>
          ))}
        </section>
      )}

      <section className="space-y-3 rounded-xl border border-slate-200 bg-white p-4">
        <SiteFeelingsChart siteId={obs.site_id} />
      </section>

      <section className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-semibold text-brand-900">FHIR Export</h2>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => void loadFhir()}
            className="min-h-touch rounded-xl border border-slate-300 bg-white/80 px-3 text-sm font-semibold shadow-sm"
          >
            {showFhir ? 'Reload FHIR' : 'View FHIR'}
          </button>
          <button
            type="button"
            onClick={() => void handleSendFhir()}
            disabled={sending}
            className="min-h-touch rounded-xl bg-brand-700 px-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            {sending ? 'Sending…' : 'Send to FHIR test server'}
          </button>
        </div>

        {fhirError && (
          <p className="text-sm text-red-700" role="alert">
            {fhirError}
          </p>
        )}

        {sendResult && (
          <div
            className={[
              'rounded-lg px-3 py-2 text-sm',
              sendResult.ok ? 'bg-green-50 text-green-900' : 'bg-red-50 text-red-900',
            ].join(' ')}
          >
            {sendResult.ok ? (
              <>
                <p className="font-medium">✓ Sent successfully</p>
                <p className="text-xs">
                  HTTP {sendResult.http_status}
                  {sendResult.fhir_sent_at && (
                    <> · {new Date(sendResult.fhir_sent_at).toLocaleString()}</>
                  )}
                </p>
                {sendResult.excluded?.length > 0 && (
                  <p className="mt-1 text-xs">
                    Excluded fields: {sendResult.excluded.join(', ')}
                  </p>
                )}
                {sendResult.server_response && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs underline">
                      Server response
                    </summary>
                    <pre className="mt-1 overflow-x-auto text-xs">
                      {JSON.stringify(sendResult.server_response, null, 2)}
                    </pre>
                  </details>
                )}
              </>
            ) : (
              <p>✗ {sendResult.error || 'Send failed'}</p>
            )}
          </div>
        )}

        {showFhir && fhirData && (
          <details className="rounded-lg border border-slate-300 bg-slate-50">
            <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
              FHIR JSON ({fhirData.bundle?.entry?.length ?? 0} resources)
            </summary>
            <pre className="overflow-x-auto border-t border-slate-300 bg-white p-3 text-xs">
              {JSON.stringify(fhirData, null, 2)}
            </pre>
          </details>
        )}
      </section>

      <div className="flex flex-col gap-2">
        <Link
          to="/observe"
          className="inline-flex min-h-touch items-center justify-center rounded-xl bg-brand-700 font-semibold text-white"
        >
          New observation
        </Link>
        <Link
          to="/map"
          className="inline-flex min-h-touch items-center justify-center rounded-xl border border-slate-300 font-semibold"
        >
          View on map
        </Link>
      </div>
    </div>
  )
}
