export type TraceStatus = 'OK' | 'ERROR' | 'UNSET' | string

export interface TraceSummary {
  id: string
  project_id: string
  name: string
  start_time: string | null
  end_time: string | null
  duration_ms: number | null
  status: TraceStatus
  error: string | null
}

export interface Span {
  id: string
  trace_id: string
  parent_span_id: string | null
  name: string
  type: string
  start_time: string | null
  end_time: string | null
  duration_ms: number | null
  status: TraceStatus
  error: string | null
  metadata: Record<string, unknown> | string | null
}

export interface TraceDetail extends TraceSummary {
  spans: Span[]
}

export interface ProjectMetrics {
  trace_count: number
  error_count: number
  error_rate: number
  average_duration_ms: number
  input_tokens: number
}

export interface EvaluationResult {
  id: string
  project_id: string
  trace_id: string
  metric_name: string
  score: number
  confidence: number | null
  evaluator_version: string
  details: Record<string, unknown> | null
  created_at: string
}

export interface EvaluationSummary {
  metric_name: string
  average_score: number
  average_confidence: number | null
  evaluation_count: number
}
