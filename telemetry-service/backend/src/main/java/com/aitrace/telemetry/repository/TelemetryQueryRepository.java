package com.aitrace.telemetry.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Map;

@Repository
public class TelemetryQueryRepository {

    private final JdbcTemplate jdbcTemplate;

    public TelemetryQueryRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<Map<String, Object>> findTraces(String projectId, int limit) {
        return jdbcTemplate.queryForList(
                """
                SELECT id, project_id, name, start_time, end_time, duration_ms, status, error
                FROM traces
                WHERE project_id = ?
                ORDER BY start_time DESC NULLS LAST
                LIMIT ?
                """,
                projectId, limit
        );
    }

    public Map<String, Object> findTrace(String traceId) {
        List<Map<String, Object>> traces = jdbcTemplate.queryForList(
                "SELECT id, project_id, name, start_time, end_time, duration_ms, status, error " +
                        "FROM traces WHERE id = ?", traceId
        );
        if (traces.isEmpty()) {
            return null;
        }

        Map<String, Object> trace = traces.get(0);
        trace.put("spans", jdbcTemplate.queryForList(
                """
                SELECT id, trace_id, parent_span_id, name, type, start_time, end_time,
                       duration_ms, status, error, metadata
                FROM spans
                WHERE trace_id = ?
                ORDER BY start_time ASC NULLS LAST
                """,
                traceId
        ));
        return trace;
    }

    public Map<String, Object> metrics(String projectId) {
        return jdbcTemplate.queryForMap(
                """
                WITH project_traces AS (
                    SELECT id, duration_ms, status
                    FROM traces
                    WHERE project_id = ?
                ), trace_metrics AS (
                    SELECT COUNT(*) AS trace_count,
                           COUNT(*) FILTER (WHERE status = 'ERROR') AS error_count,
                           COALESCE(AVG(duration_ms), 0) AS average_duration_ms
                    FROM project_traces
                ), token_metrics AS (
                    SELECT COALESCE(SUM(COALESCE(
                               NULLIF(s.metadata->>'input_tokens', '')::numeric,
                               NULLIF(s.metadata->>'prompt_tokens', '')::numeric,
                               0
                           )), 0)
                           AS input_tokens
                    FROM spans s
                    WHERE s.trace_id IN (SELECT id FROM project_traces)
                )
                SELECT trace_count, error_count,
                       CASE WHEN trace_count = 0 THEN 0
                            ELSE ROUND((error_count::numeric / trace_count) * 100, 2)
                       END AS error_rate,
                       average_duration_ms, input_tokens
                FROM trace_metrics CROSS JOIN token_metrics
                """,
                projectId
        );
    }

    public List<Map<String, Object>> findEvaluations(String projectId, int limit) {
        return jdbcTemplate.queryForList(
                """
                SELECT id, project_id, trace_id, metric_name, score, confidence,
                       evaluator_version, details, created_at
                FROM evaluations
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                projectId, limit
        );
    }

    public List<Map<String, Object>> evaluationSummary(String projectId) {
        return jdbcTemplate.queryForList(
                """
                SELECT metric_name,
                       AVG(score) AS average_score,
                       AVG(confidence) AS average_confidence,
                       COUNT(*) AS evaluation_count
                FROM evaluations
                WHERE project_id = ?
                GROUP BY metric_name
                ORDER BY metric_name
                """,
                projectId
        );
    }
}
