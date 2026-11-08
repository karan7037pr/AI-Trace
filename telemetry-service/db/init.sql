CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS traces (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_ms DOUBLE PRECISION,
    status TEXT NOT NULL,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS spans (
    id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES traces(id),
    parent_span_id TEXT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    duration_ms DOUBLE PRECISION,
    status TEXT NOT NULL,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS spans_trace_id_idx ON spans(trace_id);

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
