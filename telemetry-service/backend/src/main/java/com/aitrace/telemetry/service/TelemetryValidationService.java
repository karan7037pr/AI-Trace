package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.TelemetryBatch;
import com.aitrace.telemetry.model.TelemetryEvent;
import org.springframework.stereotype.Service;

import java.util.Set;

@Service
public class TelemetryValidationService {

    private static final int MAX_EVENTS_PER_BATCH = 20;
    private static final Set<String> EVENT_TYPES = Set.of("TRACE", "SPAN");

    public void validate(TelemetryBatch batch) {
        if (batch == null || isBlank(batch.projectId())) {
            throw new IllegalArgumentException("project_id is required");
        }
        if (batch.events() == null || batch.events().isEmpty()) {
            throw new IllegalArgumentException("events must not be empty");
        }
        if (batch.events().size() > MAX_EVENTS_PER_BATCH) {
            throw new IllegalArgumentException("a batch cannot contain more than 20 events");
        }

        for (TelemetryEvent event : batch.events()) {
            if (event == null) {
                throw new IllegalArgumentException("events cannot contain null values");
            }
            if (isBlank(event.eventId()) || isBlank(event.eventType()) || isBlank(event.traceId())) {
                throw new IllegalArgumentException("event_id, event_type, and trace_id are required");
            }
            if (!EVENT_TYPES.contains(event.eventType())) {
                throw new IllegalArgumentException("event_type must be TRACE or SPAN");
            }
            if ("SPAN".equals(event.eventType()) && isBlank(event.spanId())) {
                throw new IllegalArgumentException("span_id is required for SPAN events");
            }
        }
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
