package com.aitrace.telemetry.model;

import com.fasterxml.jackson.databind.annotation.JsonNaming;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;

import java.util.List;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record EvaluationJob(
        String projectId,
        String traceId,
        String input,
        String output,
        List<String> context,
        List<String> evaluators
) {
}
