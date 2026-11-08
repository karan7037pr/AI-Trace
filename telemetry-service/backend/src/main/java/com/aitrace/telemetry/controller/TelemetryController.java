package com.aitrace.telemetry.controller;

import com.aitrace.telemetry.model.TelemetryBatch;
import com.aitrace.telemetry.service.KafkaTelemetryProducer;
import com.aitrace.telemetry.service.TelemetryValidationService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/v1/telemetry")
public class TelemetryController {

    private final TelemetryValidationService validationService;
    private final KafkaTelemetryProducer producer;

    public TelemetryController(
            TelemetryValidationService validationService,
            KafkaTelemetryProducer producer
    ) {
        this.validationService = validationService;
        this.producer = producer;
    }

    @PostMapping("/batches")
    public ResponseEntity<Map<String, Object>> ingest(@RequestBody TelemetryBatch batch) {
        validationService.validate(batch);
        batch.events().forEach(event -> producer.publish(event.withProjectId(batch.projectId())));

        return ResponseEntity.accepted().body(Map.of(
                "accepted", true,
                "event_count", batch.events().size()
        ));
    }
}
