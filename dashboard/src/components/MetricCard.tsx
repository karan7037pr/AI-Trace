export default function MetricCard({ label, value, detail, accent }: { label: string; value: string; detail?: string; accent?: string }) {
  return <article className="metric-card">
    <div className="metric-label">{label}</div>
    <div className={`metric-value ${accent ?? ''}`}>{value}</div>
    {detail && <div className="metric-detail">{detail}</div>}
  </article>
}
