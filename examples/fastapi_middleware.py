"""
ARGUS-AI + FastAPI Integration Example

Production middleware that scores every LLM response served
through a FastAPI endpoint and exposes Prometheus metrics.

Usage:
    pip install "argus-llm[prometheus]" fastapi uvicorn
    python examples/fastapi_middleware.py

Then:
    curl -X POST http://localhost:8000/chat \
      -H "Content-Type: application/json" \
      -d '{"prompt": "What is machine learning?"}'

    # G-ARVIS metrics at:
    curl http://localhost:8000/metrics

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import argus_ai
from argus_ai.monitoring.thresholds import ThresholdConfig
from argus_ai.monitoring.alerts import AlertRule, AlertSeverity

# --- App Setup ---

app = FastAPI(title="ARGUS-AI Demo API", version="0.1.0")

# Initialize ARGUS with production thresholds
argus_client = argus_ai.init(
    profile="enterprise",
    thresholds=ThresholdConfig(
        composite_min=0.70,
        safety_min=0.85,
        accuracy_min=0.65,
    ),
    alert_rules=[
        AlertRule(
            dimension="safety",
            threshold=0.80,
            severity=AlertSeverity.CRITICAL,
            message="Safety score below production minimum",
        ),
    ],
    exporters=["console"],
    on_alert=lambda msg, result: print(f"ALERT: {msg}"),
)


# --- Request/Response Models ---

class ChatRequest(BaseModel):
    prompt: str
    context: Optional[str] = None
    model: str = "claude-sonnet-4"


class ChatResponse(BaseModel):
    response: str
    garvis_composite: float
    garvis_passing: bool
    scores: dict
    alerts: list[str]
    latency_ms: float


# --- Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Chat endpoint with inline G-ARVIS scoring."""
    start = time.perf_counter()

    # Simulate LLM call (replace with actual provider)
    llm_response = _simulate_llm(req.prompt)
    llm_latency = (time.perf_counter() - start) * 1000

    # Score with G-ARVIS
    result = argus_client.evaluate(
        prompt=req.prompt,
        response=llm_response,
        context=req.context,
        model_name=req.model,
        latency_ms=llm_latency,
    )

    total_latency = (time.perf_counter() - start) * 1000

    return ChatResponse(
        response=llm_response,
        garvis_composite=result.garvis_composite,
        garvis_passing=result.passing,
        scores={
            "groundedness": result.groundedness,
            "accuracy": result.accuracy,
            "reliability": result.reliability,
            "variance": result.variance,
            "inference_cost": result.inference_cost,
            "safety": result.safety,
        },
        alerts=result.alerts,
        latency_ms=round(total_latency, 1),
    )


@app.get("/health")
async def health():
    """Health check with monitor stats."""
    stats = argus_client._monitor.get_stats()
    return {
        "status": "healthy",
        "argus_version": argus_ai.__version__,
        "monitor_stats": stats,
    }


# --- LLM Simulation (replace with real provider) ---

def _simulate_llm(prompt: str) -> str:
    """Placeholder for actual LLM API call."""
    time.sleep(0.05)  # Simulate latency
    return (
        f"Based on the question about '{prompt[:50]}', "
        "the key points are: this is a simulated response "
        "demonstrating the ARGUS-AI FastAPI integration pattern. "
        "In production, replace this with your Anthropic or "
        "OpenAI client call."
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
