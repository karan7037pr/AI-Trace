package com.aitrace.telemetry.controller;

import com.aitrace.telemetry.repository.TelemetryQueryRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
public class QueryController {

    private final TelemetryQueryRepository repository;

    public QueryController(TelemetryQueryRepository repository) {
        this.repository = repository;
    }

    @GetMapping("/projects/{projectId}/traces")
    public List<Map<String, Object>> listTraces(
            @PathVariable String projectId,
            @RequestParam(defaultValue = "50") int limit
    ) {
        int safeLimit = Math.max(1, Math.min(limit, 100));
        return repository.findTraces(projectId, safeLimit);
    }

    @GetMapping("/traces/{traceId}")
    public ResponseEntity<Map<String, Object>> getTrace(@PathVariable String traceId) {
        Map<String, Object> trace = repository.findTrace(traceId);
        return trace == null ? ResponseEntity.notFound().build() : ResponseEntity.ok(trace);
    }

    @GetMapping("/projects/{projectId}/metrics")
    public Map<String, Object> metrics(@PathVariable String projectId) {
        return repository.metrics(projectId);
    }

    @GetMapping("/projects/{projectId}/evaluations")
    public List<Map<String, Object>> evaluations(
            @PathVariable String projectId,
            @RequestParam(defaultValue = "50") int limit
    ) {
        int safeLimit = Math.max(1, Math.min(limit, 100));
        return repository.findEvaluations(projectId, safeLimit);
    }

    @GetMapping("/projects/{projectId}/evaluation-summary")
    public List<Map<String, Object>> evaluationSummary(@PathVariable String projectId) {
        return repository.evaluationSummary(projectId);
    }
}
