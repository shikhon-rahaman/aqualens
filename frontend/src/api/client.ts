import type {
  AnalyzeResponse,
  EvaluateResponse,
  FeelingsAnswers,
  FieldSource,
  FormSchema,
  ObservationOut,
  PhotoRole,
  Site,
} from '../types'

export type HealthResponse = {
  status: string
  ai_chain: string[]
  db: string
}

const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (body.detail) detail = JSON.stringify(body.detail)
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return (await response.json()) as T
}

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`)
  return parseJson<HealthResponse>(response)
}

export async function fetchFormSchema(): Promise<FormSchema> {
  const response = await fetch(`${API_BASE}/api/form-schema`)
  return parseJson<FormSchema>(response)
}

export async function fetchSites(lat?: number, lon?: number): Promise<Site[]> {
  const params = new URLSearchParams()
  if (lat !== undefined && lon !== undefined) {
    params.set('lat', String(lat))
    params.set('lon', String(lon))
  }
  const qs = params.toString()
  const response = await fetch(`${API_BASE}/api/sites${qs ? `?${qs}` : ''}`)
  const body = await parseJson<{ sites: Site[] }>(response)
  return body.sites
}

export async function createSite(input: {
  name: string
  code: string
  lat: number
  lon: number
}): Promise<Site> {
  const response = await fetch(`${API_BASE}/api/sites`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  return parseJson<Site>(response)
}

const PHOTO_FORM_KEYS: Record<PhotoRole, string> = {
  upstream: 'photo_upstream',
  downstream: 'photo_downstream',
  context: 'photo_context',
  biodiversity: 'photo_biodiversity',
}

export async function analyzePhotos(
  photos: Partial<Record<PhotoRole, Blob>>,
): Promise<AnalyzeResponse> {
  const form = new FormData()
  for (const role of Object.keys(PHOTO_FORM_KEYS) as PhotoRole[]) {
    const blob = photos[role]
    if (!blob) continue
    form.append(PHOTO_FORM_KEYS[role], blob, `${role}.jpg`)
  }
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: 'POST',
    body: form,
  })
  return parseJson<AnalyzeResponse>(response)
}

export async function evaluateObservation(input: {
  site_id?: string | null
  user_lat?: number | null
  user_lon?: number | null
  facing_downstream: boolean
  answers: Record<string, unknown>
  field_sources: Record<string, FieldSource>
  ai_suggestions: AnalyzeResponse['suggestions']
  include_context?: boolean
}): Promise<EvaluateResponse> {
  const response = await fetch(`${API_BASE}/api/observations/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      site_id: input.site_id ?? undefined,
      user_lat: input.user_lat ?? undefined,
      user_lon: input.user_lon ?? undefined,
      facing_downstream: input.facing_downstream,
      answers: input.answers,
      field_sources: input.field_sources,
      ai_suggestions: input.ai_suggestions,
      include_context: input.include_context ?? false,
    }),
  })
  return parseJson<EvaluateResponse>(response)
}

export async function createObservation(input: {
  site_id: string
  facing_downstream: boolean
  user_lat: number | null
  user_lon: number | null
  answers: Record<string, unknown>
  field_sources: Record<string, FieldSource>
  ai_suggestions: AnalyzeResponse['suggestions']
  feelings: FeelingsAnswers | null
  overall_user: string | null
  photos: Partial<Record<PhotoRole, Blob>>
}): Promise<ObservationOut> {
  const form = new FormData()
  form.append('site_id', input.site_id)
  form.append('facing_downstream', String(input.facing_downstream))
  if (input.user_lat != null) form.append('user_lat', String(input.user_lat))
  if (input.user_lon != null) form.append('user_lon', String(input.user_lon))
  form.append('answers', JSON.stringify(input.answers))
  form.append('field_sources', JSON.stringify(input.field_sources))
  form.append('ai_suggestions', JSON.stringify(input.ai_suggestions))
  if (input.feelings) form.append('feelings', JSON.stringify(input.feelings))
  if (input.overall_user) form.append('overall_user', input.overall_user)
  form.append('status', 'confirmed')

  for (const role of Object.keys(PHOTO_FORM_KEYS) as PhotoRole[]) {
    const blob = input.photos[role]
    if (!blob) continue
    form.append(PHOTO_FORM_KEYS[role], blob, `${role}.jpg`)
  }

  const response = await fetch(`${API_BASE}/api/observations`, {
    method: 'POST',
    body: form,
  })
  return parseJson<ObservationOut>(response)
}

export async function fetchObservation(id: string): Promise<ObservationOut> {
  const response = await fetch(`${API_BASE}/api/observations/${id}`)
  return parseJson<ObservationOut>(response)
}

export async function fetchObservationFhir(id: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/observations/${id}/fhir`)
  return parseJson(response)
}

export async function sendObservationToFhir(id: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/observations/${id}/fhir/send`, {
    method: 'POST',
  })
  return parseJson(response)
}

export async function fetchObservationsList(params?: {
  needs_expert?: boolean
  bbox?: string
}): Promise<{ observations: any[] }> {
  const searchParams = new URLSearchParams()
  if (params?.needs_expert !== undefined) {
    searchParams.set('needs_expert', String(params.needs_expert))
  }
  if (params?.bbox) {
    searchParams.set('bbox', params.bbox)
  }
  const qs = searchParams.toString()
  const response = await fetch(
    `${API_BASE}/api/observations${qs ? `?${qs}` : ''}`,
  )
  return parseJson(response)
}

export async function fetchExpertQueue(pin: string): Promise<{ observations: any[] }> {
  const response = await fetch(`${API_BASE}/api/queue`, {
    headers: { 'X-Expert-Pin': pin },
  })
  return parseJson(response)
}

export async function expertReviewObservation(
  id: string,
  pin: string,
  action: 'approve' | 'correct',
  answers?: Record<string, unknown>,
  fieldSources?: Record<string, string>,
): Promise<ObservationOut> {
  const form = new FormData()
  form.append('action', action)
  if (answers) form.append('answers', JSON.stringify(answers))
  if (fieldSources) form.append('field_sources', JSON.stringify(fieldSources))

  const response = await fetch(`${API_BASE}/api/observations/${id}/review`, {
    method: 'POST',
    headers: { 'X-Expert-Pin': pin },
    body: form,
  })
  return parseJson(response)
}
