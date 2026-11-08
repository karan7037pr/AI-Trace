"""A tiny demonstration of the first AITrace milestone."""

import json
import time

from aitrace_sdk import Trace


trace = Trace("question-answering")

with trace.span("retrieve-documents", "RETRIEVAL") as retrieval:
    retrieval.set_metadata("top_k", 3)
    time.sleep(0.01)

    with trace.span("rerank-documents", "RERANKING") as reranking:
        reranking.set_metadata("model", "demo-reranker")
        time.sleep(0.005)

with trace.span("generate-answer", "LLM") as generation:
    generation.set_metadata("model", "demo-model")
    generation.set_metadata("input_tokens", 120)
    generation.set_metadata("output_tokens", 42)
    time.sleep(0.01)

trace.finish()

print(json.dumps(trace.to_dict(), indent=2))
