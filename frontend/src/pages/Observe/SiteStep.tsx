import { useEffect, useRef, useState, type FormEvent } from 'react'
import { createSite, fetchSites } from '../../api/client'
import { formatDistance, getBrowserLocation } from '../../lib/geo'
import type { FormField, Site } from '../../types'
import { SiteMap } from '../../components/SiteMap'

type Props = {
  siteField: FormField | undefined
  selected: Site | null
  userLat: number | null
  userLon: number | null
  onUserLocation: (lat: number | null, lon: number | null) => void
  onSelect: (site: Site) => void
  onContinue: () => void
}

export function SiteStep({
  siteField,
  selected,
  userLat,
  userLon,
  onUserLocation,
  onSelect,
  onContinue,
}: Props) {
  const [sites, setSites] = useState<Site[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [geoMessage, setGeoMessage] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [pickLat, setPickLat] = useState<number | null>(null)
  const [pickLon, setPickLon] = useState<number | null>(null)
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [saving, setSaving] = useState(false)
  const onUserLocationRef = useRef(onUserLocation)
  useEffect(() => {
    onUserLocationRef.current = onUserLocation
  }, [onUserLocation])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      const geo = await getBrowserLocation()
      if (cancelled) return
      let lat: number | undefined
      let lon: number | undefined
      if (geo.status === 'ok') {
        lat = geo.lat
        lon = geo.lon
        onUserLocationRef.current(geo.lat, geo.lon)
        setGeoMessage(null)
      } else {
        onUserLocationRef.current(null, null)
        setGeoMessage(geo.message)
      }
      try {
        const list = await fetchSites(lat, lon)
        if (!cancelled) setSites(list)
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Could not load sites')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const lat = pickLat ?? userLat
    const lon = pickLon ?? userLon
    if (lat == null || lon == null) {
      setError('Set a map pin or allow location before adding a site.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const site = await createSite({
        name: name.trim(),
        code: code.trim().toUpperCase(),
        lat,
        lon,
      })
      setSites((prev) => [site, ...prev])
      onSelect(site)
      setShowAdd(false)
      setName('')
      setCode('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create site')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-4" aria-labelledby="site-step-title">
      <header className="space-y-1">
        <p className="text-sm font-medium text-brand-500">Step 1 of 3</p>
        <h1 id="site-step-title" className="text-2xl font-bold text-brand-900">
          {siteField?.question ?? 'Which research site is this?'}
        </h1>
        <p className="text-slate-600">
          {siteField?.help ??
            'Pick the nearest listed site, or add a new informal site if none fit.'}
        </p>
      </header>

      {geoMessage && (
        <p className="rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
          {geoMessage}
        </p>
      )}
      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-slate-600">Finding nearby sites…</p>
      ) : (
        <>
          <SiteMap
            sites={sites}
            selectedId={selected?.id ?? null}
            userLat={userLat}
            userLon={userLon}
            onSelect={(id) => {
              const site = sites.find((s) => s.id === id)
              if (site) onSelect(site)
            }}
            onMapClick={
              showAdd
                ? (lat, lon) => {
                    setPickLat(lat)
                    setPickLon(lon)
                  }
                : undefined
            }
            pickLat={showAdd ? pickLat : null}
            pickLon={showAdd ? pickLon : null}
          />

          <ul className="space-y-2" aria-label="Sites">
            {sites.map((site) => {
              const isSelected = selected?.id === site.id
              return (
                <li key={site.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(site)}
                    className={[
                      'flex min-h-touch w-full flex-col items-start rounded-xl border px-4 py-3 text-left transition',
                      isSelected
                        ? 'border-brand-700 bg-brand-50 ring-2 ring-brand-500'
                        : 'border-slate-200 bg-white hover:border-brand-500',
                    ].join(' ')}
                    aria-pressed={isSelected}
                  >
                    <span className="font-semibold text-brand-900">{site.name}</span>
                    <span className="text-sm text-slate-600">
                      {site.code}
                      {site.is_demo ? ' · Demo data' : ''}
                      {' · '}
                      {formatDistance(site.distance_m)}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>

          {!showAdd ? (
            <button
              type="button"
              className="min-h-touch w-full rounded-xl border border-dashed border-brand-500 px-4 text-base font-semibold text-brand-700"
              onClick={() => setShowAdd(true)}
            >
              Add a new site
            </button>
          ) : (
            <form
              onSubmit={handleCreate}
              className="space-y-3 rounded-xl border border-slate-200 bg-white p-4"
            >
              <h2 className="text-lg font-semibold text-brand-900">New site</h2>
              <p className="text-sm text-slate-600">
                Tap the map to place a pin
                {userLat != null ? ', or we will use your current location.' : '.'}
              </p>
              <label className="block space-y-1">
                <span className="text-sm font-medium">Name</span>
                <input
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="min-h-touch w-full rounded-lg border border-slate-300 px-3"
                  autoComplete="off"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-sm font-medium">Short code</span>
                <input
                  required
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="min-h-touch w-full rounded-lg border border-slate-300 px-3 uppercase"
                  autoComplete="off"
                  maxLength={64}
                />
              </label>
              <p className="text-sm text-slate-600">
                Pin:{' '}
                {pickLat != null && pickLon != null
                  ? `${pickLat.toFixed(5)}, ${pickLon.toFixed(5)}`
                  : userLat != null && userLon != null
                    ? `${userLat.toFixed(5)}, ${userLon.toFixed(5)} (your location)`
                    : 'not set'}
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="min-h-touch flex-1 rounded-lg border border-slate-300 font-medium"
                  onClick={() => setShowAdd(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="min-h-touch flex-1 rounded-lg bg-brand-700 font-semibold text-white disabled:opacity-60"
                >
                  {saving ? 'Saving…' : 'Save site'}
                </button>
              </div>
            </form>
          )}

          <button
            type="button"
            disabled={!selected}
            onClick={onContinue}
            className="min-h-touch w-full rounded-xl bg-brand-700 px-4 text-base font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Continue to photos
          </button>
        </>
      )}
    </section>
  )
}
