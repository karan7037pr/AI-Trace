CREATE TABLE IF NOT EXISTS evaluations (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION,
    evaluator_version TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trace_id, metric_name, evaluator_version)
);

CREATE INDEX IF NOT EXISTS evaluations_project_id_idx ON evaluations(project_id);
CREATE INDEX IF NOT EXISTS evaluations_trace_id_idx ON evaluations(trace_id);
