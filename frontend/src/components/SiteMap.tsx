import { useEffect } from 'react'
import {
  MapContainer,
  Marker,
  TileLayer,
  useMap,
  useMapEvents,
} from 'react-leaflet'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import type { Site } from '../types'

import 'leaflet/dist/leaflet.css'

// Fix default marker icons under Vite bundling.
const DefaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
})
L.Marker.prototype.options.icon = DefaultIcon

type Props = {
  sites: Site[]
  selectedId: string | null
  userLat: number | null
  userLon: number | null
  onSelect: (siteId: string) => void
  onMapClick?: (lat: number, lon: number) => void
  pickLat?: number | null
  pickLon?: number | null
}

function FitBounds({
  sites,
  userLat,
  userLon,
}: {
  sites: Site[]
  userLat: number | null
  userLon: number | null
}) {
  const map = useMap()
  useEffect(() => {
    const points: L.LatLngExpression[] = sites.map((s) => [s.lat, s.lon])
    if (userLat != null && userLon != null) {
      points.push([userLat, userLon])
    }
    if (points.length === 0) {
      map.setView([20, 0], 2)
      return
    }
    if (points.length === 1) {
      map.setView(points[0], 14)
      return
    }
    map.fitBounds(L.latLngBounds(points), { padding: [28, 28], maxZoom: 15 })
  }, [map, sites, userLat, userLon])
  return null
}

function ClickCatcher({
  onMapClick,
}: {
  onMapClick?: (lat: number, lon: number) => void
}) {
  useMapEvents({
    click(e) {
      onMapClick?.(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

export function SiteMap({
  sites,
  selectedId,
  userLat,
  userLon,
  onSelect,
  onMapClick,
  pickLat,
  pickLon,
}: Props) {
  const center: [number, number] =
    userLat != null && userLon != null
      ? [userLat, userLon]
      : sites[0]
        ? [sites[0].lat, sites[0].lon]
        : [20, 0]

  return (
    <div className="h-56 w-full overflow-hidden rounded-2xl border border-slate-200/80 bg-white/70 shadow-[0_12px_28px_rgba(15,76,92,0.08)]">
      <MapContainer
        center={center}
        zoom={13}
        className="h-full w-full"
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds sites={sites} userLat={userLat} userLon={userLon} />
        <ClickCatcher onMapClick={onMapClick} />
        {userLat != null && userLon != null && (
          <Marker position={[userLat, userLon]} title="You are here" />
        )}
        {sites.map((site) => (
          <Marker
            key={site.id}
            position={[site.lat, site.lon]}
            opacity={selectedId === site.id ? 1 : 0.75}
            eventHandlers={{
              click: () => onSelect(site.id),
            }}
            title={site.name}
          />
        ))}
        {pickLat != null && pickLon != null && (
          <Marker position={[pickLat, pickLon]} title="New site pin" />
        )}
      </MapContainer>
    </div>
  )
}
