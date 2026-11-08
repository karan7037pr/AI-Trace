package com.aitrace.telemetry.model;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.annotation.JsonNaming;

import com.fasterxml.jackson.databind.PropertyNamingStrategies;

import java.time.Instant;
import java.util.Map;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record TelemetryEvent(
        String projectId,
        String eventId,
        String eventType,
        String traceId,
        String spanId,
        String parentSpanId,
        String name,
        String type,
        Instant startTime,
        Instant endTime,
        Double durationMs,
        String status,
        String error,
        Map<String, JsonNode> metadata
) {
    public TelemetryEvent withProjectId(String value) {
        return new TelemetryEvent(
                value, eventId, eventType, traceId, spanId, parentSpanId, name, type,
                startTime, endTime, durationMs, status, error, metadata
        );
    }
}
