"""Core data types for ARGUS-AI evaluation pipeline."""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MetricDomain(str, Enum):
    """Classification of which G-ARVIS dimension a metric belongs to."""

    GROUNDEDNESS = "groundedness"
    ACCURACY = "accuracy"
    RELIABILITY = "reliability"
    VARIANCE = "variance"
    INFERENCE_COST = "inference_cost"
    SAFETY = "safety"
    # Agentic extensions
    AGENT_STABILITY = "agent_stability"
    ERROR_RECOVERY = "error_recovery"
    COST_PER_STEP = "cost_per_completed_step"


class EvalRequest(BaseModel):
    """Input to the ARGUS evaluation pipeline.

    Represents a single LLM interaction to be scored across all
    G-ARVIS dimensions.
    """

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    response: str
    context: Optional[str] = None
    ground_truth: Optional[str] = None
    model_name: Optional[str] = None
    latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class MetricResult(BaseModel):
    """Result of a single metric evaluation."""

    name: str
    domain: MetricDomain
    score: float = Field(ge=0.0, le=1.0)
    details: dict[str, Any] = Field(default_factory=dict)
    computation_ms: float = 0.0


class EvalResult(BaseModel):
    """Complete evaluation output with all G-ARVIS scores."""

    request_id: str
    garvis_composite: float = Field(ge=0.0, le=1.0)
    groundedness: float = Field(ge=0.0, le=1.0)
    accuracy: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    variance: float = Field(ge=0.0, le=1.0)
    inference_cost: float = Field(ge=0.0, le=1.0)
    safety: float = Field(ge=0.0, le=1.0)
    metric_details: list[MetricResult] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)
    evaluation_ms: float = 0.0

    @property
    def passing(self) -> bool:
        """Whether composite score meets minimum threshold (0.7)."""
        return self.garvis_composite >= 0.7

    def to_flat_dict(self) -> dict[str, Any]:
        """Export as flat dictionary for logging and metrics export."""
        return {
            "request_id": self.request_id,
            "garvis_composite": round(self.garvis_composite, 4),
            "groundedness": round(self.groundedness, 4),
            "accuracy": round(self.accuracy, 4),
            "reliability": round(self.reliability, 4),
            "variance": round(self.variance, 4),
            "inference_cost": round(self.inference_cost, 4),
            "safety": round(self.safety, 4),
            "passing": self.passing,
            "alert_count": len(self.alerts),
            "evaluation_ms": round(self.evaluation_ms, 2),
            "timestamp": self.timestamp,
        }


class AgenticEvalRequest(EvalRequest):
    """Extended request type for agentic workflow evaluation.

    Adds fields needed for ASF (Agent Stability Factor),
    ERR (Error Recovery Rate), and CPCS (Cost Per Completed Step).
    """

    steps_planned: int = 0
    steps_completed: int = 0
    steps_failed: int = 0
    steps_recovered: int = 0
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    total_cost_usd: float = 0.0
    retries: int = 0
    workflow_id: Optional[str] = None
