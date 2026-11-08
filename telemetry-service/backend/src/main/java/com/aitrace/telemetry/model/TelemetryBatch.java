package com.aitrace.telemetry.model;

import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;

import java.util.List;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record TelemetryBatch(
        String projectId,
        List<TelemetryEvent> events
) {
}
