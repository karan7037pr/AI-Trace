import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchTrace } from '../api/client'
import SpanTimeline from '../components/SpanTimeline'
import StatusBadge from '../components/StatusBadge'
import type { TraceDetail } from '../types/telemetry'

export default function TraceDetailPage() {
  const { traceId = '' } = useParams()
  const [trace, setTrace] = useState<TraceDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { void fetchTrace(traceId).then(setTrace).catch((loadError: unknown) => setError(loadError instanceof Error ? loadError.message : 'Unable to load trace')) }, [traceId])
  if (error) return <div className="error-page"><Link to="/" className="back-link">← Back to overview</Link><div className="error-banner"><strong>Trace unavailable.</strong><span>{error}</span></div></div>
  if (!trace) return <div className="loading-state">Loading trace<span className="loading-line" /></div>
  return <>
    <Link to="/" className="back-link">← Back to overview</Link>
    <section className="trace-heading"><div><div className="eyebrow">TRACE DETAIL</div><h1>{trace.name || 'unnamed trace'}</h1><div className="trace-heading-meta"><StatusBadge status={trace.status} /><code>{trace.id}</code></div></div><div className="trace-summary"><span>DURATION</span><strong>{trace.duration_ms == null ? '—' : `${Math.round(trace.duration_ms)} ms`}</strong></div></section>
    {trace.error && <div className="error-banner"><strong>Trace error</strong><span>{trace.error}</span></div>}
    <section className="panel"><div className="panel-heading"><div><div className="eyebrow">EXECUTION TREE</div><h2>{trace.spans.length} spans</h2></div><span className="updated">{trace.start_time ? new Date(trace.start_time).toLocaleString() : 'start time unavailable'}</span></div><SpanTimeline spans={trace.spans} /></section>
  </>
}
