import type { EvaluationSummary as EvaluationSummaryItem } from '../types/telemetry'

function label(metricName: string) {
  return metricName.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function percentage(value: number | null) {
  return value == null ? '—' : `${(value * 100).toFixed(1)}%`
}

export default function EvaluationSummary({ summaries }: { summaries: EvaluationSummaryItem[] }) {
  if (!summaries.length) return null
  return <div className="evaluation-summary-grid">{summaries.map((summary) => <article className="evaluation-summary-card" key={summary.metric_name}>
    <div className="metric-label">OVERALL {label(summary.metric_name).toUpperCase()}</div>
    <div className="evaluation-summary-score">{percentage(summary.average_score)}</div>
    <div className="metric-detail">{summary.evaluation_count} evaluated trace{summary.evaluation_count === 1 ? '' : 's'} · {percentage(summary.average_confidence)} confidence</div>
  </article>)}</div>
}
