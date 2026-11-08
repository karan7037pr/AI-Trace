import type { EvaluationResult, EvaluationSummary, ProjectMetrics, TraceDetail, TraceSummary } from '../types/telemetry'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api/v1').replace(/\/$/, '')
const RAG_API_BASE_URL = (import.meta.env.VITE_RAG_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

async function ragRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${RAG_API_BASE_URL}${path}`, options)
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string }
    throw new Error(body.detail ?? `RAG API request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export function fetchMetrics(projectId: string): Promise<ProjectMetrics> {
  return get<ProjectMetrics>(`/projects/${encodeURIComponent(projectId)}/metrics`)
}

export function fetchTraces(projectId: string, limit = 50): Promise<TraceSummary[]> {
  return get<TraceSummary[]>(`/projects/${encodeURIComponent(projectId)}/traces?limit=${limit}`)
}

export function fetchTrace(traceId: string): Promise<TraceDetail> {
  return get<TraceDetail>(`/traces/${encodeURIComponent(traceId)}`)
}

export function fetchEvaluations(projectId: string, limit = 50): Promise<EvaluationResult[]> {
  return get<EvaluationResult[]>(`/projects/${encodeURIComponent(projectId)}/evaluations?limit=${limit}`)
}

export function fetchEvaluationSummary(projectId: string): Promise<EvaluationSummary[]> {
  return get<EvaluationSummary[]>(`/projects/${encodeURIComponent(projectId)}/evaluation-summary`)
}

export interface UploadedDocument {
  id: string
  filename: string
  page_count: number
  chunk_count: number
}

export interface ChatResponse {
  trace_id: string
  answer: string
  sources: Array<{ filename: string; page_number: number; similarity: number }>
  analytics: { duration_ms: number; input_tokens: number | null; output_tokens: number | null }
}

export interface RAGEvaluation {
  metric_name: string
  score: number
  confidence: number | null
}

export function uploadDocuments(workspaceId: string, files: File[]): Promise<{ documents: UploadedDocument[] }> {
  const form = new FormData()
  form.append('workspace_id', workspaceId)
  files.forEach((file) => form.append('files', file))
  return ragRequest<{ documents: UploadedDocument[] }>('/api/documents/upload', { method: 'POST', body: form })
}

export function askDocument(workspaceId: string, question: string): Promise<ChatResponse> {
  return ragRequest<ChatResponse>('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ workspace_id: workspaceId, question }) })
}

export function evaluateRun(workspaceId: string, traceId: string): Promise<{ evaluations: RAGEvaluation[] }> {
  return ragRequest<{ evaluations: RAGEvaluation[] }>(`/api/evaluations/${encodeURIComponent(traceId)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ workspace_id: workspaceId }) })
}

export const dashboardConfig = {
  apiBaseUrl: API_BASE_URL,
  projectId: import.meta.env.VITE_PROJECT_ID ?? 'local-project',
  ragApiBaseUrl: RAG_API_BASE_URL,
}
