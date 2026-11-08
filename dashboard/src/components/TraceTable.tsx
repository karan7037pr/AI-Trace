import { Link } from 'react-router-dom'
import type { TraceSummary } from '../types/telemetry'
import StatusBadge from './StatusBadge'

function formatDuration(duration: number | null) {
  return duration == null ? '—' : `${Math.round(duration)} ms`
}

function formatTime(value: string | null) {
  if (!value) return 'time unavailable'
  return new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function TraceTable({ traces }: { traces: TraceSummary[] }) {
  if (traces.length === 0) return <div className="empty-state"><strong>No traces yet</strong><span>Run your instrumented RAG application and refresh this page.</span></div>
  return <div className="table-wrap"><table>
    <thead><tr><th>TRACE</th><th>STATUS</th><th>LATENCY</th><th>STARTED</th><th>TRACE ID</th></tr></thead>
    <tbody>{traces.map((trace) => <tr key={trace.id}>
      <td><Link className="trace-link" to={`/traces/${encodeURIComponent(trace.id)}`}>{trace.name || 'unnamed trace'}</Link></td>
      <td><StatusBadge status={trace.status} /></td>
      <td className="mono">{formatDuration(trace.duration_ms)}</td>
      <td className="muted">{formatTime(trace.start_time)}</td>
      <td className="mono trace-id">{trace.id}</td>
    </tr>)}</tbody>
  </table></div>
}
