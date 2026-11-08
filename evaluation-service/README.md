# AITrace Jev Evaluation Worker

This worker consumes sampled evaluation jobs from Kafka, sends them to Jev,
and stores only evaluation scores in telemetry PostgreSQL. It never needs to
expose the Jev key to the browser.

Install and run locally:

```bash
cd evaluation-service
python -m pip install -r requirements.txt
export JEV_API_KEY="your-rotated-key"
python evaluator_worker.py
```

The worker expects Kafka on `localhost:9092` and telemetry PostgreSQL on
`localhost:5433` by default.
