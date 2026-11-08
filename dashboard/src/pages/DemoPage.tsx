import { useMemo, useState, type ChangeEvent, type FormEvent } from 'react'
import { askDocument, evaluateRun, uploadDocuments, type ChatResponse, type RAGEvaluation, type UploadedDocument } from '../api/client'

function workspaceId() {
  const key = 'aitrace-demo-workspace'
  const existing = window.localStorage.getItem(key)
  if (existing) return existing
  const created = crypto.randomUUID()
  window.localStorage.setItem(key, created)
  return created
}

function percent(value: number | null) { return value == null ? '—' : `${Math.round(value * 100)}%` }

export default function DemoPage() {
  const workspace = useMemo(workspaceId, [])
  const [documents, setDocuments] = useState<UploadedDocument[]>([])
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<ChatResponse | null>(null)
  const [evaluations, setEvaluations] = useState<RAGEvaluation[]>([])
  const [busy, setBusy] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [message, setMessage] = useState('Upload a PDF to create your private demo workspace.')

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    if (!files.length) return
    setBusy(true); setMessage('Extracting pages, chunking text, and creating embeddings...')
    try { const result = await uploadDocuments(workspace, files); setDocuments((current) => [...current, ...result.documents]); setMessage(`${result.documents.length} document(s) ready for questions.`) }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Upload failed.') }
    finally { setBusy(false); event.target.value = '' }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault(); if (!question.trim()) return
    setBusy(true); setEvaluations([]); setMessage('Searching your document and generating an answer...')
    try { const result = await askDocument(workspace, question); setAnswer(result); setMessage('Answer ready. Evaluate it with Jev when you are ready.') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Question failed.') }
    finally { setBusy(false) }
  }

  async function handleEvaluate() {
    if (!answer) return
    setEvaluating(true); setMessage('Jev is evaluating faithfulness, relevance, and context precision...')
    try { const result = await evaluateRun(workspace, answer.trace_id); setEvaluations(result.evaluations); setMessage('Evaluation complete.') }
    catch (error) { setMessage(error instanceof Error ? error.message : 'Evaluation failed.') }
    finally { setEvaluating(false) }
  }

  return <div className="demo-page">
    <section className="hero-panel"><div><div className="eyebrow">AITrace / DOCUMENT RAG LAB</div><h1>Ask your documents.<br /><span>See why the answer works.</span></h1><p>Upload a PDF, search it with local embeddings, generate a grounded answer, and inspect its performance and quality signals.</p></div><div className="hero-status"><span className="pulse-dot" />LIVE DEMO<br /><small>workspace {workspace.slice(0, 8)}</small></div></section>
    <section className="demo-grid">
      <div className="demo-column">
        <article className="demo-card upload-card"><div className="card-kicker">01 / INGEST</div><h2>Load your knowledge</h2><p>PDF text is extracted, split into overlapping chunks, and embedded locally before it reaches pgvector.</p><label className={`upload-dropzone ${busy ? 'disabled' : ''}`}><input type="file" accept="application/pdf" multiple onChange={handleUpload} disabled={busy} /><span className="upload-icon">↑</span><strong>Drop PDFs here</strong><small>or click to browse · 10 MB per file</small></label>{documents.length > 0 && <div className="document-list">{documents.map((document) => <div className="document-item" key={document.id}><span className="file-icon">PDF</span><div><strong>{document.filename}</strong><small>{document.page_count} pages · {document.chunk_count} chunks</small></div><span className="ready-dot" /></div>)}</div>}</article>
        <article className="demo-card ask-card"><div className="card-kicker">02 / RETRIEVE + GENERATE</div><h2>Ask a question</h2><form onSubmit={handleAsk}><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What is the main idea of this document?" rows={4} /><button className="primary-button" disabled={busy || !documents.length}>{busy ? 'Working...' : 'Ask your documents →'}</button></form><div className="status-message">{message}</div></article>
      </div>
      <div className="demo-column result-column">
        <article className="demo-card answer-card"><div className="card-kicker">03 / OBSERVE</div><div className="answer-header"><h2>Answer</h2>{answer && <code>{answer.trace_id.slice(0, 12)}...</code>}</div>{answer ? <><div className="answer-text">{answer.answer}</div><div className="source-list"><div className="subheading">SOURCE SIGNALS</div>{answer.sources.map((source, index) => <div className="source-item" key={`${source.filename}-${source.page_number}-${index}`}><span>0{index + 1}</span><strong>{source.filename}</strong><small>page {source.page_number} · similarity {source.similarity.toFixed(2)}</small></div>)}</div><div className="analytics-strip"><div><small>LATENCY</small><strong>{Math.round(answer.analytics.duration_ms)} ms</strong></div><div><small>INPUT TOKENS</small><strong>{answer.analytics.input_tokens ?? '—'}</strong></div><div><small>OUTPUT TOKENS</small><strong>{answer.analytics.output_tokens ?? '—'}</strong></div></div><button className="evaluate-button" onClick={handleEvaluate} disabled={evaluating}>{evaluating ? 'Evaluating...' : '✦ Evaluate this answer'}</button></> : <div className="answer-empty"><span>✦</span><strong>Your grounded answer will appear here.</strong><small>Upload a PDF and ask something to begin.</small></div>}</article>
        {evaluations.length > 0 && <article className="demo-card quality-card"><div className="card-kicker">04 / QUALITY</div><div className="answer-header"><h2>Jev evaluation</h2><span className="quality-tag">AUTOMATIC</span></div><div className="quality-grid">{evaluations.map((evaluation) => <div className="quality-metric" key={evaluation.metric_name}><small>{evaluation.metric_name.replaceAll('_', ' ').toUpperCase()}</small><strong>{percent(evaluation.score)}</strong><span>{percent(evaluation.confidence)} confidence</span></div>)}</div></article>}
      </div>
    </section>
  </div>
}
