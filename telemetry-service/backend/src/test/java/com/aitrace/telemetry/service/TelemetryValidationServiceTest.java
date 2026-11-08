package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.TelemetryBatch;
import com.aitrace.telemetry.model.TelemetryEvent;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;

class TelemetryValidationServiceTest {

    private final TelemetryValidationService service = new TelemetryValidationService();

    @Test
    void acceptsValidTraceEvent() {
        TelemetryEvent event = new TelemetryEvent(
                "project-1", "event-1", "TRACE", "trace-1", null, null,
                "demo", null, null, null, null, "OK", null, Map.of()
        );

        assertDoesNotThrow(() -> service.validate(new TelemetryBatch("project-1", List.of(event))));
    }

    @Test
    void rejectsEmptyBatch() {
        assertThrows(IllegalArgumentException.class,
                () -> service.validate(new TelemetryBatch("project-1", List.of())));
    }

    @Test
    void rejectsSpanWithoutSpanId() {
        TelemetryEvent event = new TelemetryEvent(
                "project-1", "event-1", "SPAN", "trace-1", null, null,
                "retrieve", "RETRIEVAL", null, null, null, "OK", null, Map.of()
        );

        assertThrows(IllegalArgumentException.class,
                () -> service.validate(new TelemetryBatch("project-1", List.of(event))));
    }
}
