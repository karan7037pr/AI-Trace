import type { TraceStatus } from '../types/telemetry'

export default function StatusBadge({ status }: { status: TraceStatus }) {
  const normalized = status.toLowerCase()
  const tone = normalized === 'ok' || normalized === 'success' ? 'success' : normalized === 'error' || normalized === 'failed' ? 'danger' : 'neutral'
  return <span className={`status-badge ${tone}`}><span className="status-dot" />{status || 'UNKNOWN'}</span>
}
