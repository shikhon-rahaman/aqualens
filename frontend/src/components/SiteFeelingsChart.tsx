import { useEffect, useState } from 'react'

type FeelingsData = {
  joy: number
  serenity: number
  anger: number
  fear: number
  count: number
}

export function SiteFeelingsChart({ siteId }: { siteId: string }) {
  const [data, setData] = useState<FeelingsData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // In a real implementation, this would fetch aggregated feelings data
    // For now, simulate with demo data
    const timer = setTimeout(() => {
      setData({
        joy: 3.2,
        serenity: 3.8,
        anger: 1.5,
        fear: 1.8,
        count: 12,
      })
      setLoading(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [siteId])

  if (loading) {
    return <p className="text-sm text-slate-600">Loading feelings data…</p>
  }

  if (!data || data.count === 0) {
    return (
      <p className="text-sm text-slate-600">
        No feelings data available for this site yet.
      </p>
    )
  }

  const feelings = [
    { key: 'joy', label: 'Joy', value: data.joy, color: '#22c55e' },
    { key: 'serenity', label: 'Serenity', value: data.serenity, color: '#3b82f6' },
    { key: 'anger', label: 'Anger', value: data.anger, color: '#ef4444' },
    { key: 'fear', label: 'Fear', value: data.fear, color: '#a855f7' },
  ]

  const maxValue = 5

  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold text-brand-900">
          Average feelings at this site
        </h3>
        <span className="text-xs text-slate-500">n={data.count}</span>
      </div>

      <div className="space-y-2">
        {feelings.map((feeling) => (
          <div key={feeling.key} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium capitalize text-slate-700">
                {feeling.label}
              </span>
              <span className="text-slate-600">
                {feeling.value.toFixed(1)} / {maxValue}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-slate-100">
              <div
                className="h-2 rounded-full transition-all"
                style={{
                  width: `${(feeling.value / maxValue) * 100}%`,
                  backgroundColor: feeling.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-slate-500">
        ⚠ Demo data. Association only, not proof of cause. Real aggregation
        requires multiple citizen reports.
      </p>
    </div>
  )
}
