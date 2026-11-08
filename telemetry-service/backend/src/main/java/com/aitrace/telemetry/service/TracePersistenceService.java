package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.TelemetryEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.Map;

@Service
public class TracePersistenceService {

    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;

    public TracePersistenceService(JdbcTemplate jdbcTemplate, ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public void persist(TelemetryEvent event) {
        if ("TRACE".equals(event.eventType())) {
            persistTrace(event);
        } else if ("SPAN".equals(event.eventType())) {
            persistSpan(event);
        } else {
            throw new IllegalArgumentException("Unsupported event_type: " + event.eventType());
        }
    }

    private void persistTrace(TelemetryEvent event) {
        jdbcTemplate.update(
                """
                INSERT INTO projects (id, name)
                VALUES (?, ?)
                ON CONFLICT (id) DO NOTHING
                """,
                event.projectId(), event.projectId()
        );

        jdbcTemplate.update(
                """
                INSERT INTO traces
                    (id, project_id, name, start_time, end_time, duration_ms, status, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    project_id = EXCLUDED.project_id,
                    name = EXCLUDED.name,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    duration_ms = EXCLUDED.duration_ms,
                    status = EXCLUDED.status,
                    error = EXCLUDED.error
                """,
                event.traceId(), event.projectId(), event.name(), timestamp(event.startTime()),
                timestamp(event.endTime()), event.durationMs(), event.status(), event.error()
        );
    }

    private void persistSpan(TelemetryEvent event) {
        jdbcTemplate.update(
                "INSERT INTO projects (id, name) VALUES (?, ?) ON CONFLICT (id) DO NOTHING",
                event.projectId(), event.projectId()
        );
        jdbcTemplate.update(
                """
                INSERT INTO traces (id, project_id, name, status)
                VALUES (?, ?, 'unknown', 'RUNNING')
                ON CONFLICT (id) DO NOTHING
                """,
                event.traceId(), event.projectId()
        );

        jdbcTemplate.update(
                """
                INSERT INTO spans
                    (id, trace_id, parent_span_id, name, type, start_time, end_time,
                     duration_ms, status, error, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CAST(? AS jsonb))
                ON CONFLICT (id) DO UPDATE SET
                    trace_id = EXCLUDED.trace_id,
                    parent_span_id = EXCLUDED.parent_span_id,
                    name = EXCLUDED.name,
                    type = EXCLUDED.type,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    duration_ms = EXCLUDED.duration_ms,
                    status = EXCLUDED.status,
                    error = EXCLUDED.error,
                    metadata = EXCLUDED.metadata
                """,
                event.spanId(), event.traceId(), event.parentSpanId(), event.name(), event.type(),
                timestamp(event.startTime()), timestamp(event.endTime()), event.durationMs(),
                event.status(), event.error(), metadataJson(event.metadata())
        );
    }

    private Timestamp timestamp(Instant instant) {
        return instant == null ? null : Timestamp.from(instant);
    }

    private String metadataJson(Map<String, ?> metadata) {
        try {
            return objectMapper.writeValueAsString(metadata == null ? Map.of() : metadata);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Telemetry metadata is not valid JSON", exception);
        }
    }
}
