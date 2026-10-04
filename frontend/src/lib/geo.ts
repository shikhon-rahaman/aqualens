export type GeoResult =
  | { status: 'ok'; lat: number; lon: number }
  | { status: 'denied'; message: string }
  | { status: 'unavailable'; message: string }

export function getBrowserLocation(
  timeoutMs = 12000,
): Promise<GeoResult> {
  if (!('geolocation' in navigator)) {
    return Promise.resolve({
      status: 'unavailable',
      message: 'This browser does not support location.',
    })
  }

  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        resolve({
          status: 'ok',
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
        })
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          resolve({
            status: 'denied',
            message:
              'Location permission was denied. You can still pick a site from the list or add a new one.',
          })
          return
        }
        resolve({
          status: 'unavailable',
          message:
            'Could not get your location. You can still pick a site from the list or add a new one.',
        })
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60_000 },
    )
  })
}

export function formatDistance(meters: number | null | undefined): string {
  if (meters == null || Number.isNaN(meters)) return 'Distance unknown'
  if (meters < 1000) return `${Math.round(meters)} m away`
  return `${(meters / 1000).toFixed(1)} km away`
}
