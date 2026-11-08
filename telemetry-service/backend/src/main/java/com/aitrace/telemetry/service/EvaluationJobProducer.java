package com.aitrace.telemetry.service;

import com.aitrace.telemetry.model.EvaluationJob;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class EvaluationJobProducer {

    private final KafkaTemplate<String, EvaluationJob> kafkaTemplate;
    private final String topic;

    public EvaluationJobProducer(
            KafkaTemplate<String, EvaluationJob> kafkaTemplate,
            @Value("${aitrace.kafka.evaluation-topic}") String topic
    ) {
        this.kafkaTemplate = kafkaTemplate;
        this.topic = topic;
    }

    public void publish(EvaluationJob job) {
        try {
            kafkaTemplate.send(topic, job.traceId(), job).get();
        } catch (Exception exception) {
            throw new IllegalStateException("Kafka did not acknowledge evaluation job", exception);
        }
    }
}
