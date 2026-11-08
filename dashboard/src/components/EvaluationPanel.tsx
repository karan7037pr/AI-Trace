import { Link } from 'react-router-dom'
import type { EvaluationResult } from '../types/telemetry'

function label(metricName: string) {
  return metricName.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function score(value: number) {
  return `${Math.round(value * 100)}%`
}

export default function EvaluationPanel({ evaluations }: { evaluations: EvaluationResult[] }) {
  if (!evaluations.length) return <div className="empty-state"><strong>No evaluation data yet</strong><span>Enable content sampling and start the Jev worker to evaluate traces.</span></div>
  return <div className="evaluation-list">{evaluations.map((evaluation) => <div className="evaluation-row" key={evaluation.id}>
    <div><strong>{label(evaluation.metric_name)}</strong><span className="evaluation-version">{evaluation.evaluator_version}</span></div>
    <div className="evaluation-score">{score(evaluation.score)}{evaluation.confidence != null && <small>{Math.round(evaluation.confidence * 100)}% confidence</small>}</div>
    <Link className="trace-link mono" to={`/traces/${encodeURIComponent(evaluation.trace_id)}`}>view trace →</Link>
  </div>)}</div>
}
