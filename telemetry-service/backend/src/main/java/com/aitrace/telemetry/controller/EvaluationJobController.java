package com.aitrace.telemetry.controller;

import com.aitrace.telemetry.model.EvaluationJob;
import com.aitrace.telemetry.service.EvaluationJobProducer;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/evaluation-jobs")
public class EvaluationJobController {

    private final EvaluationJobProducer producer;

    public EvaluationJobController(EvaluationJobProducer producer) {
        this.producer = producer;
    }

    @PostMapping
    public ResponseEntity<Map<String, Object>> create(@RequestBody EvaluationJob job) {
        validate(job);
        producer.publish(job);
        return ResponseEntity.accepted().body(Map.of(
                "accepted", true,
                "trace_id", job.traceId()
        ));
    }

    private void validate(EvaluationJob job) {
        if (job == null || blank(job.projectId()) || blank(job.traceId())) {
            throw new IllegalArgumentException("project_id and trace_id are required");
        }
        if (blank(job.input()) || blank(job.output())) {
            throw new IllegalArgumentException("input and output are required");
        }
        if (job.context() == null || job.context().isEmpty()) {
            throw new IllegalArgumentException("context must not be empty");
        }
        if (job.evaluators() == null || job.evaluators().isEmpty()) {
            throw new IllegalArgumentException("evaluators must not be empty");
        }
    }

    private boolean blank(String value) {
        return value == null || value.isBlank();
    }
}
