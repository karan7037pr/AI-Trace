package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.TelemetryEvent;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

@Service
public class TelemetryConsumer {

    private final ObjectMapper objectMapper;
    private final TracePersistenceService persistenceService;

    public TelemetryConsumer(ObjectMapper objectMapper, TracePersistenceService persistenceService) {
        this.objectMapper = objectMapper;
        this.persistenceService = persistenceService;
    }

    @KafkaListener(
            topics = "${aitrace.kafka.telemetry-topic}",
            groupId = "${spring.kafka.consumer.group-id}"
    )
    public void consume(String payload) {
        try {
            TelemetryEvent event = objectMapper.readValue(payload, TelemetryEvent.class);
            persistenceService.persist(event);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("Kafka telemetry payload is invalid JSON", exception);
        }
    }
}
