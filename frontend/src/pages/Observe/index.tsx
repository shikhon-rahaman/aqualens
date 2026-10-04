import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchFormSchema } from '../../api/client'
import type {
  AnalyzeResponse,
  EvaluateResponse,
  FeelingsAnswers,
  FieldSource,
  FormField,
  FormSchema,
  PhotoRole,
  PhotoSlot,
  Site,
} from '../../types'
import { defaultFeelings } from '../../lib/feelings'
import { AnalyzeStep } from './AnalyzeStep'
import { FeelingsStep } from './FeelingsStep'
import { FinalReviewStep } from './FinalReviewStep'
import { OverallStep } from './OverallStep'
import { PhotosStep } from './PhotosStep'
import { ReviewStep } from './ReviewStep'
import { SiteStep } from './SiteStep'

const DRAFT_KEY = 'aqualens.observe.draft.v1'

type Step =
  | 'site'
  | 'photos'
  | 'analyze'
  | 'review'
  | 'overall'
  | 'feelings'
  | 'final'

type PersistedDraft = {
  site: Site | null
  facingDownstream: boolean | null
  analyze: AnalyzeResponse | null
  userLat: number | null
  userLon: number | null
  answers: Record<string, unknown>
  fieldSources: Record<string, FieldSource>
  feelings: FeelingsAnswers | null
  step?: Step
}

function loadPersisted(): PersistedDraft | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    return JSON.parse(raw) as PersistedDraft
  } catch {
    return null
  }
}

function savePersisted(draft: PersistedDraft) {
  sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
}

export function ObservePage() {
  const navigate = useNavigate()
  const persisted = loadPersisted()
  const [step, setStep] = useState<Step>(() =>
    persisted?.analyze && persisted?.site ? 'review' : 'site',
  )
  const [schema, setSchema] = useState<FormSchema | null>(null)
  const [schemaError, setSchemaError] = useState<string | null>(null)
  const [site, setSite] = useState<Site | null>(persisted?.site ?? null)
  const [facingDownstream, setFacingDownstream] = useState<boolean | null>(
    persisted?.facingDownstream ?? null,
  )
  const [photos, setPhotos] = useState<Partial<Record<PhotoRole, PhotoSlot>>>({})
  const [analyze, setAnalyze] = useState<AnalyzeResponse | null>(
    persisted?.analyze ?? null,
  )
  const [userLat, setUserLat] = useState<number | null>(persisted?.userLat ?? null)
  const [userLon, setUserLon] = useState<number | null>(persisted?.userLon ?? null)
  const [answers, setAnswers] = useState<Record<string, unknown>>(
    persisted?.answers ?? {},
  )
  const [fieldSources, setFieldSources] = useState<Record<string, FieldSource>>(
    persisted?.fieldSources ?? {},
  )
  const [feelings, setFeelings] = useState<FeelingsAnswers>(
    persisted?.feelings ?? defaultFeelings(),
  )
  const [evaluate, setEvaluate] = useState<EvaluateResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    fetchFormSchema()
      .then((data) => {
        if (!cancelled) setSchema(data)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSchemaError(
            err instanceof Error ? err.message : 'Could not load form schema',
          )
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    savePersisted({
      site,
      facingDownstream,
      analyze,
      userLat,
      userLon,
      answers,
      fieldSources,
      feelings,
      step,
    })
  }, [
    site,
    facingDownstream,
    analyze,
    userLat,
    userLon,
    answers,
    fieldSources,
    feelings,
    step,
  ])

  const siteField = useMemo(
    () => schema?.fields.find((f) => f.id === 'site'),
    [schema],
  )
  const mediaFields = useMemo(
    () =>
      (schema?.fields ?? []).filter(
        (f: FormField) => f.value_type === 'media' && f.id.startsWith('photo_'),
      ),
    [schema],
  )
  const overallField = useMemo(
    () => schema?.fields.find((f) => f.id === 'overall_assessment'),
    [schema],
  )
  const feelingsField = useMemo(
    () => schema?.fields.find((f) => f.id === 'feelings'),
    [schema],
  )

  function setPhoto(role: PhotoRole, slot: PhotoSlot | null) {
    setPhotos((prev) => {
      const next = { ...prev }
      if (slot == null) delete next[role]
      else next[role] = slot
      return next
    })
  }

  function restart() {
    Object.values(photos).forEach((p) => {
      if (p) URL.revokeObjectURL(p.previewUrl)
    })
    setPhotos({})
    setAnalyze(null)
    setFacingDownstream(null)
    setAnswers({})
    setFieldSources({})
    setFeelings(defaultFeelings())
    setEvaluate(null)
    setStep('site')
    sessionStorage.removeItem(DRAFT_KEY)
  }

  if (schemaError) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-bold text-brand-900">Observe</h1>
        <p className="rounded-lg bg-red-50 px-3 py-2 text-red-800" role="alert">
          {schemaError}
        </p>
      </div>
    )
  }

  if (!schema) {
    return <p className="text-slate-600">Loading questions…</p>
  }

  if (step === 'site') {
    return (
      <SiteStep
        siteField={siteField}
        selected={site}
        userLat={userLat}
        userLon={userLon}
        onUserLocation={(lat, lon) => {
          setUserLat(lat)
          setUserLon(lon)
        }}
        onSelect={setSite}
        onContinue={() => setStep('photos')}
      />
    )
  }

  if (step === 'photos') {
    return (
      <PhotosStep
        mediaFields={mediaFields}
        photos={photos}
        facingDownstream={facingDownstream}
        onPhoto={setPhoto}
        onFacingChange={setFacingDownstream}
        onBack={() => setStep('site')}
        onContinue={() => setStep('analyze')}
      />
    )
  }

  if (step === 'analyze' && site && facingDownstream !== null) {
    return (
      <AnalyzeStep
        site={site}
        facingDownstream={facingDownstream}
        photos={photos}
        onBack={() => setStep('photos')}
        onDone={(result) => {
          setAnalyze(result)
          setStep('review')
        }}
      />
    )
  }

  if (step === 'review' && site && facingDownstream !== null) {
    return (
      <ReviewStep
        schemaFields={schema.fields}
        site={site}
        facingDownstream={facingDownstream}
        userLat={userLat}
        userLon={userLon}
        analyze={analyze}
        answers={answers}
        fieldSources={fieldSources}
        onAnswersChange={(nextAnswers, nextSources) => {
          setAnswers(nextAnswers)
          setFieldSources(nextSources)
        }}
        onEvaluate={setEvaluate}
        onBack={() => setStep('analyze')}
        onContinue={() => setStep('overall')}
      />
    )
  }

  if (step === 'overall') {
    return (
      <OverallStep
        overallField={overallField}
        evaluate={evaluate}
        initial={
          typeof answers.overall_assessment === 'string'
            ? answers.overall_assessment
            : null
        }
        onBack={() => setStep('review')}
        onContinue={(overall) => {
          setAnswers((prev) => ({ ...prev, overall_assessment: overall }))
          setFieldSources((prev) => ({
            ...prev,
            overall_assessment: 'human',
          }))
          setStep('feelings')
        }}
      />
    )
  }

  if (step === 'feelings') {
    return (
      <FeelingsStep
        feelingsField={feelingsField}
        value={feelings}
        onChange={setFeelings}
        onBack={() => setStep('overall')}
        onContinue={() => setStep('final')}
      />
    )
  }

  if (step === 'final' && site && facingDownstream !== null) {
    return (
      <FinalReviewStep
        schemaFields={schema.fields}
        site={site}
        facingDownstream={facingDownstream}
        userLat={userLat}
        userLon={userLon}
        answers={answers}
        fieldSources={fieldSources}
        feelings={feelings}
        analyze={analyze}
        photos={photos}
        onBack={() => setStep('feelings')}
        onSaved={(id) => {
          sessionStorage.removeItem(DRAFT_KEY)
          navigate(`/result/${id}`)
        }}
      />
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-slate-600">Something went wrong in the flow.</p>
      <button
        type="button"
        className="min-h-touch rounded-xl bg-brand-700 px-4 font-semibold text-white"
        onClick={restart}
      >
        Start over
      </button>
    </div>
  )
}
