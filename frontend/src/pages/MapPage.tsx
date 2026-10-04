import { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import { Icon } from 'leaflet'
import { Link } from 'react-router-dom'
import { fetchObservationsList } from '../api/client'
import 'leaflet/dist/leaflet.css'

type ObsSummary = {
  id: string
  site_id: string
  site_name: string | null
  lat: number | null
  lon: number | null
  status: string
  needs_expert: boolean
  risk_contact: string | null
  risk_ecosystem: string | null
  overall_user: string | null
  is_synthetic: boolean
  captured_at: string
}

const RISK_COLORS: Record<string, string> = {
  good: '#22c55e',
  moderate: '#eab308',
  poor: '#ef4444',
}

function getRiskColor(risk: string | null): string {
  return RISK_COLORS[risk || 'moderate'] || '#94a3b8'
}

function createMarkerIcon(color: string): Icon {
  return new Icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(`
      <svg xmlns="http://www.w3.org/2000/svg" width="25" height="41" viewBox="0 0 25 41">
        <path fill="${color}" stroke="#000" stroke-width="1.5" d="M12.5 0C5.596 0 0 5.596 0 12.5c0 9.375 12.5 28.5 12.5 28.5S25 21.875 25 12.5C25 5.596 19.404 0 12.5 0z"/>
        <circle cx="12.5" cy="12.5" r="6" fill="#fff"/>
      </svg>
    `)}`,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  })
}

export function MapPage() {
  const [observations, setObservations] = useState<ObsSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterRisk, setFilterRisk] = useState<string | null>(null)
  const [filterNeedsReview, setFilterNeedsReview] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchObservationsList()
      .then((data) => {
        if (!cancelled) {
          setObservations(data.observations)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load observations')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p className="text-slate-600">Loading map…</p>
  }

  if (error) {
    return (
      <p className="rounded-lg bg-red-50 px-3 py-2 text-red-800" role="alert">
        {error}
      </p>
    )
  }

  const withCoords = observations.filter(
    (o) => o.lat !== null && o.lon !== null,
  ) as Array<ObsSummary & { lat: number; lon: number }>

  const filtered = withCoords.filter((o) => {
    if (filterNeedsReview && !o.needs_expert) return false
    if (filterRisk && o.risk_ecosystem !== filterRisk) return false
    return true
  })

  const center: [number, number] =
    filtered.length > 0 ? [filtered[0].lat, filtered[0].lon] : [51.505, -0.09]

  return (
    <div className="space-y-4">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold text-brand-900">Observation Map</h1>
        <p className="text-slate-600">
          {filtered.length} observation{filtered.length !== 1 ? 's' : ''} shown
          {observations.some((o) => o.is_synthetic) && (
            <span className="ml-2 rounded bg-slate-100 px-2 py-0.5 text-xs">
              Demo data included
            </span>
          )}
        </p>
      </header>

      <section className="glass-card flex flex-wrap gap-2 p-3">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={filterNeedsReview}
            onChange={(e) => setFilterNeedsReview(e.target.checked)}
          />
          Needs review only
        </label>
        <span className="text-slate-300">|</span>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="risk"
            checked={filterRisk === null}
            onChange={() => setFilterRisk(null)}
          />
          All risks
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="risk"
            checked={filterRisk === 'good'}
            onChange={() => setFilterRisk('good')}
          />
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: RISK_COLORS.good }}
          />
          Good
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="risk"
            checked={filterRisk === 'moderate'}
            onChange={() => setFilterRisk('moderate')}
          />
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: RISK_COLORS.moderate }}
          />
          Moderate
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="risk"
            checked={filterRisk === 'poor'}
            onChange={() => setFilterRisk('poor')}
          />
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: RISK_COLORS.poor }}
          />
          Poor
        </label>
      </section>

      <div className="h-[500px] overflow-hidden rounded-2xl border border-slate-200/80 bg-white/70 shadow-[0_12px_32px_rgba(15,76,92,0.08)]">
        <MapContainer
          center={center}
          zoom={13}
          scrollWheelZoom={true}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {filtered.map((obs) => (
            <Marker
              key={obs.id}
              position={[obs.lat, obs.lon]}
              icon={createMarkerIcon(getRiskColor(obs.risk_ecosystem))}
            >
              <Popup>
                <div className="space-y-1 p-1">
                  <p className="font-semibold text-brand-900">
                    {obs.site_name ?? 'Unknown site'}
                  </p>
                  <p className="text-sm">
                    Risk:{' '}
                    <strong className="capitalize">
                      {obs.risk_ecosystem ?? '—'}
                    </strong>
                  </p>
                  {obs.overall_user && (
                    <p className="text-sm">
                      Citizen rating:{' '}
                      <strong className="capitalize">{obs.overall_user}</strong>
                    </p>
                  )}
                  {obs.needs_expert && (
                    <p className="rounded bg-amber-50 px-2 py-1 text-xs text-amber-900">
                      Needs expert review
                    </p>
                  )}
                  {obs.is_synthetic && (
                    <p className="text-xs text-slate-500">Demo data</p>
                  )}
                  <Link
                    to={`/result/${obs.id}`}
                    className="mt-2 inline-block rounded-xl bg-brand-700 px-2 py-1 text-xs font-medium text-white"
                  >
                    View details
                  </Link>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      <div className="flex gap-2">
        <Link
          to="/observe"
          className="inline-flex min-h-touch items-center justify-center rounded-xl bg-brand-700 px-4 font-semibold text-white"
        >
          New observation
        </Link>
      </div>
    </div>
  )
}
