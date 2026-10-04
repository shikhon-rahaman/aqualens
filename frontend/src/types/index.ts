/** Shared TypeScript types for AquaLens frontend. */

export type FieldSource = 'ai_accepted' | 'ai_edited' | 'human' | 'unanswered'

export type AiRole = 'suggest' | 'human_only' | 'candidates_only' | 'none'
export type ValueType = 'choice' | 'number' | 'feelings' | 'text' | 'site' | 'media'

export type FormField = {
  id: string
  group: string
  question: string
  help: string
  ai_role: AiRole
  value_type: ValueType
  values: string[] | null
  value_labels: Record<string, string> | null
  pending: boolean
  pending_note: string | null
}

export type FormSchema = {
  version: string
  fields: FormField[]
  pending_notes: Record<string, string>
}

export type Site = {
  id: string
  name: string
  code: string
  lat: number
  lon: number
  is_demo: boolean
  distance_m: number | null
}

export type PhotoRole = 'upstream' | 'downstream' | 'context' | 'biodiversity'

export type PhotoSlot = {
  role: PhotoRole
  blob: Blob
  previewUrl: string
}

export type FieldSuggestion = {
  value: string
  confidence: number
  reason: string
}

export type AnalyzeResponse = {
  status: 'ok' | 'ai_unavailable'
  suggestions: Record<string, FieldSuggestion>
  message?: string
  upstream_vs_downstream?: string | null
  needs_expert_hints?: string[]
  provider_used?: string | null
  roles_analyzed?: string[]
}

export type FeelingEntry = { value: number | null; na: boolean }

export type FeelingsAnswers = {
  joy: FeelingEntry
  serenity: FeelingEntry
  anger: FeelingEntry
  fear: FeelingEntry
}

export type ValidationFlag = {
  code: string
  fields: string[]
  message: string
  severity: string
  needs_expert: boolean
}

export type EvaluateResponse = {
  flags: ValidationFlag[]
  needs_expert: boolean
  overall_suggested: string
  overall_pressure_count: number
  overall_mismatch_levels: number | null
  risk: {
    contact: { level: string; reasons: string[] }
    ecosystem: { level: string; reasons: string[] }
    disclaimer: string
  }
  context: {
    rainfall_48h_mm: number | null
    temperature_c: number | null
    water_nearby: string
  }
}

export type ObservationOut = {
  id: string
  site_id: string
  site_name: string | null
  status: string
  needs_expert: boolean
  overall_user: string | null
  overall_suggested: string | null
  risk_contact: string | null
  risk_ecosystem: string | null
  risk_reasons: Record<string, unknown> | null
  flags: ValidationFlag[]
  is_synthetic: boolean
  site_lat: number | null
  site_lon: number | null
  user_lat: number | null
  user_lon: number | null
  facing_downstream: boolean
  captured_at: string
  photos: Record<string, string>
  answers: Record<string, unknown>
  ai_suggestions: Record<string, unknown>
  field_sources: Record<string, FieldSource>
  feelings: FeelingsAnswers | null
  fhir_sent_at: string | null
}

export type ObserveDraft = {
  site: Site | null
  facingDownstream: boolean | null
  photos: Partial<Record<PhotoRole, PhotoSlot>>
  analyze: AnalyzeResponse | null
  userLat: number | null
  userLon: number | null
  answers: Record<string, unknown>
  fieldSources: Record<string, FieldSource>
  feelings: FeelingsAnswers | null
  evaluate: EvaluateResponse | null
}
