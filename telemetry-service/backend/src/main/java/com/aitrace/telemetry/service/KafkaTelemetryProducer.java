package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.TelemetryEvent;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class KafkaTelemetryProducer {

    private final KafkaTemplate<String, TelemetryEvent> kafkaTemplate;
    private final String topic;

    public KafkaTelemetryProducer(
            KafkaTemplate<String, TelemetryEvent> kafkaTemplate,
            @Value("${aitrace.kafka.telemetry-topic}") String topic
    ) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
    }

    public void publish(TelemetryEvent event) {
        try {
            kafkaTemplate.send(topic, event.traceId(), event).get();
        } catch (Exception exception) {
            throw new IllegalStateException("Kafka did not acknowledge telemetry event", exception);
        }
    }
}
