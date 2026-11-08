import type { Span } from '../types/telemetry'
import StatusBadge from './StatusBadge'

function formatDuration(value: number | null) { return value == null ? '—' : `${Math.round(value)} ms` }

function metadataText(metadata: Span['metadata']) {
  if (!metadata) return null
  if (typeof metadata === 'string') return metadata
  return JSON.stringify(metadata, null, 2)
}

export default function SpanTimeline({ spans }: { spans: Span[] }) {
  if (!spans.length) return <div className="empty-state"><strong>No spans recorded</strong><span>This trace contains no child operations.</span></div>
  const hasTimes = spans.every((span) => span.start_time && span.duration_ms != null)
  const start = hasTimes ? Math.min(...spans.map((span) => new Date(span.start_time!).getTime())) : 0
  const total = hasTimes ? Math.max(...spans.map((span) => new Date(span.start_time!).getTime() - start + (span.duration_ms ?? 0)), 1) : 1
  return <div className="span-list">{spans.map((span, index) => {
    const offset = hasTimes ? ((new Date(span.start_time!).getTime() - start) / total) * 100 : 0
    const width = hasTimes ? Math.max(((span.duration_ms ?? 0) / total) * 100, 1.5) : 100
    const metadata = metadataText(span.metadata)
    return <article className="span-row" key={span.id}>
      <div className="span-main">
        <div className="span-name"><span className="span-index">{String(index + 1).padStart(2, '0')}</span><strong>{span.name || 'unnamed span'}</strong><span className="span-type">{span.type || 'operation'}</span></div>
        <div className="span-meta"><StatusBadge status={span.status} /><span className="mono">{formatDuration(span.duration_ms)}</span><span className="mono muted">{span.id}</span></div>
      </div>
      <div className="timeline-track">{hasTimes && <div className={`timeline-bar ${span.status === 'ERROR' ? 'failed' : ''}`} style={{ marginLeft: `${offset}%`, width: `${width}%` }} />}</div>
      {span.error && <div className="span-error">{span.error}</div>}
      {metadata && <details className="metadata"><summary>metadata</summary><pre>{metadata}</pre></details>}
    </article>
  })}</div>
}
