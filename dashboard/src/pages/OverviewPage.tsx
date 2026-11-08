import { useCallback, useEffect, useState } from 'react'
import { fetchEvaluationSummary, fetchEvaluations, fetchMetrics, fetchTraces, dashboardConfig } from '../api/client'
import MetricCard from '../components/MetricCard'
import TraceTable from '../components/TraceTable'
import EvaluationPanel from '../components/EvaluationPanel'
import EvaluationSummary from '../components/EvaluationSummary'
import type { EvaluationResult, EvaluationSummary as EvaluationSummaryItem, ProjectMetrics, TraceSummary } from '../types/telemetry'

function formatNumber(value: number) { return new Intl.NumberFormat().format(value) }
function formatMs(value: number) { return value < 1000 ? `${Math.round(value)} ms` : `${(value / 1000).toFixed(2)} s` }

export default function OverviewPage() {
  const [metrics, setMetrics] = useState<ProjectMetrics | null>(null)
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [evaluations, setEvaluations] = useState<EvaluationResult[]>([])
  const [evaluationSummary, setEvaluationSummary] = useState<EvaluationSummaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const [nextMetrics, nextTraces, nextEvaluations, nextEvaluationSummary] = await Promise.all([fetchMetrics(dashboardConfig.projectId), fetchTraces(dashboardConfig.projectId), fetchEvaluations(dashboardConfig.projectId), fetchEvaluationSummary(dashboardConfig.projectId)])
      setMetrics(nextMetrics)
      setTraces(nextTraces)
      setEvaluations(nextEvaluations)
      setEvaluationSummary(nextEvaluationSummary)
      setLastUpdated(new Date())
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Unable to load telemetry')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load(); const timer = window.setInterval(() => void load(), 5000); return () => window.clearInterval(timer) }, [load])

  return <>
    <section className="page-heading"><div><div className="eyebrow">PROJECT / {dashboardConfig.projectId}</div><h1>System overview</h1><p>Monitor your RAG pipeline as traces move from ingestion to evaluation.</p></div><button className="refresh-button" onClick={() => void load()} disabled={loading}><span>↻</span> Refresh</button></section>
    {error && <div className="error-banner"><strong>Could not reach telemetry service.</strong><span>{error} Check that Spring Boot is running on port 8080.</span></div>}
    <section className="metric-grid">
      <MetricCard label="TOTAL TRACES" value={metrics ? formatNumber(metrics.trace_count) : '—'} detail="all recorded executions" />
      <MetricCard label="ERROR RATE" value={metrics ? `${(metrics.error_rate ?? (metrics.trace_count ? metrics.error_count / metrics.trace_count : 0) * 100).toFixed(1)}%` : '—'} detail={metrics ? `${metrics.error_count} failed traces` : 'waiting for data'} accent={metrics?.error_count ? 'danger-text' : ''} />
      <MetricCard label="AVG LATENCY" value={metrics ? formatMs(metrics.average_duration_ms) : '—'} detail="trace duration" />
      <MetricCard label="INPUT TOKENS" value={metrics ? formatNumber(metrics.input_tokens) : '—'} detail="across recorded spans" />
    </section>
    <section className="panel"><div className="panel-heading"><div><div className="eyebrow">LIVE STREAM</div><h2>Recent traces</h2></div><span className="updated">{lastUpdated ? `updated ${lastUpdated.toLocaleTimeString()}` : 'loading...'}</span></div>{loading && !traces.length ? <div className="loading-state">Loading telemetry<span className="loading-line" /></div> : <TraceTable traces={traces} />}</section>
    <section className="panel evaluation-panel"><div className="panel-heading"><div><div className="eyebrow">QUALITY SIGNALS</div><h2>Automatic evaluations</h2></div><span className="updated">Jev / sampled traces</span></div><EvaluationSummary summaries={evaluationSummary} /><EvaluationPanel evaluations={evaluations} /></section>
  </>
}
