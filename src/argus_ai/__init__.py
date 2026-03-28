"""
ARGUS-AI: Production-Grade LLM Observability

The G-ARVIS scoring engine for Groundedness, Accuracy, Reliability,
Variance, Inference Cost, and Safety monitoring of LLM applications.

Quick Start (3 lines):

    import argus_ai
    argus = argus_ai.init()
    score = argus.evaluate(prompt=prompt, response=response, context=context)

Created by Anil Prasad | Ambharii Labs
https://github.com/anilatambharii/argus-ai
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Anil Prasad"

from argus_ai.monitoring.alerts import AlertRule, AlertSeverity
from argus_ai.monitoring.thresholds import ThresholdConfig, ThresholdMonitor
from argus_ai.scoring.agentic import (
    AgentStabilityScorer,
    CostPerCompletedStepScorer,
    ErrorRecoveryScorer,
)
from argus_ai.scoring.garvis import GarvisScore, GarvisScorer
from argus_ai.scoring.metrics import (
    AccuracyScorer,
    GroundednessScorer,
    InferenceCostScorer,
    ReliabilityScorer,
    SafetyScorer,
    VarianceScorer,
)
from argus_ai.sdk.client import ArgusClient, ArgusConfig, ArgusEvaluator, init
from argus_ai.types import EvalRequest, EvalResult

__all__ = [
    # SDK entry points
    "init",
    "ArgusClient",
    "ArgusEvaluator",
    "ArgusConfig",
    # G-ARVIS scoring
    "GarvisScorer",
    "GarvisScore",
    # Individual metrics
    "GroundednessScorer",
    "AccuracyScorer",
    "ReliabilityScorer",
    "VarianceScorer",
    "InferenceCostScorer",
    "SafetyScorer",
    # Agentic metrics (ASF, ERR, CPCS)
    "AgentStabilityScorer",
    "ErrorRecoveryScorer",
    "CostPerCompletedStepScorer",
    # Monitoring
    "ThresholdMonitor",
    "ThresholdConfig",
    "AlertRule",
    "AlertSeverity",
    # Types
    "EvalRequest",
    "EvalResult",
]
