"""
ARGUS SDK Client

The primary interface for instrumenting LLM applications with
G-ARVIS scoring. Designed for 3-line integration:

    import argus_ai
    argus = argus_ai.init()
    score = argus.evaluate(prompt=prompt, response=response)

Supports:
    - Sync and async evaluation
    - Auto-export to Prometheus, OpenTelemetry, console
    - Threshold-based monitoring with alerting
    - Decorator-based instrumentation
    - Provider-specific wrappers (Anthropic, OpenAI)

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

import structlog

from argus_ai.monitoring.thresholds import ThresholdConfig, ThresholdMonitor
from argus_ai.scoring.agentic import (
    AgentStabilityScorer,
    CostPerCompletedStepScorer,
    ErrorRecoveryScorer,
)
from argus_ai.scoring.garvis import GarvisScore, GarvisScorer, GarvisWeights
from argus_ai.types import AgenticEvalRequest, EvalRequest, EvalResult, MetricResult

if TYPE_CHECKING:
    from argus_ai.monitoring.alerts import AlertRule

logger = structlog.get_logger(__name__)


@dataclass
class ArgusConfig:
    """Configuration for ArgusEvaluator/ArgusClient initialization.
    
    Attributes:
        profile: Weight profile name (enterprise, healthcare, finance, consumer, agentic).
        weights: Custom GarvisWeights (overrides profile).
        thresholds: Custom threshold configuration.
        alert_rules: List of alert rules for monitoring.
        exporters: List of exporter names (console, prometheus, otel).
        on_alert: Callback function for alert handling.
    """

    profile: str = "enterprise"
    weights: GarvisWeights | None = None
    thresholds: ThresholdConfig | None = None
    alert_rules: list[AlertRule] | None = field(default_factory=list)
    exporters: list[str] | None = field(default_factory=lambda: ["console"])
    on_alert: Callable[[str, EvalResult], None] | None = None


class ArgusClient:
    """Production-grade ARGUS client for LLM observability.

    Integrates G-ARVIS scoring, threshold monitoring, alerting,
    and metrics export into a single ergonomic interface.
    """

    def __init__(
        self,
        weights: GarvisWeights | None = None,
        profile: str = "enterprise",
        thresholds: ThresholdConfig | None = None,
        alert_rules: list[AlertRule] | None = None,
        exporters: list[str] | None = None,
        on_alert: Callable[[str, EvalResult], None] | None = None,
    ) -> None:
        self._scorer = GarvisScorer(weights=weights, profile=profile)
        self._asf_scorer = AgentStabilityScorer()
        self._err_scorer = ErrorRecoveryScorer()
        self._cpcs_scorer = CostPerCompletedStepScorer()

        # Threshold monitoring
        self._thresholds = thresholds or ThresholdConfig()
        self._monitor = ThresholdMonitor(
            config=self._thresholds,
            alert_rules=alert_rules or [],
            on_alert=on_alert,
        )

        # Metrics exporters
        self._exporters = self._init_exporters(exporters or ["console"])

        logger.info(
            "argus_client_initialized",
            profile=profile if weights is None else "custom",
            exporters=exporters or ["console"],
        )

    def evaluate(
        self,
        prompt: str,
        response: str,
        context: str | None = None,
        ground_truth: str | None = None,
        model_name: str | None = None,
        latency_ms: float | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvalResult:
        """Evaluate a single LLM interaction across all G-ARVIS dimensions.

        This is the primary method for most use cases.
        """
        request = EvalRequest(
            prompt=prompt,
            response=response,
            context=context,
            ground_truth=ground_truth,
            model_name=model_name,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            metadata=metadata or {},
        )

        result = self._scorer.evaluate(request)

        # Run threshold checks and alerting
        alerts = self._monitor.check(result)
        result.alerts = alerts

        # Export metrics
        self._export(result)

        return result

    def evaluate_request(self, request: EvalRequest) -> EvalResult:
        """Evaluate from a pre-built EvalRequest object."""
        result = self._scorer.evaluate(request)
        alerts = self._monitor.check(result)
        result.alerts = alerts
        self._export(result)
        return result

    def evaluate_agentic(
        self, request: AgenticEvalRequest
    ) -> tuple[EvalResult, list[MetricResult]]:
        """Evaluate an agentic workflow with ASF, ERR, and CPCS metrics.

        Returns the standard G-ARVIS EvalResult plus additional
        agentic metric results.
        """
        # Standard G-ARVIS evaluation
        result = self._scorer.evaluate(request)
        alerts = self._monitor.check(result)
        result.alerts = alerts

        # Agentic metrics
        agentic_metrics = [
            self._asf_scorer.score(request),
            self._err_scorer.score(request),
            self._cpcs_scorer.score(request),
        ]

        # Append to result details
        result.metric_details.extend(agentic_metrics)

        self._export(result)
        return result, agentic_metrics

    def score(
        self,
        prompt: str,
        response: str,
        context: str | None = None,
    ) -> GarvisScore:
        """Quick scoring returning a lightweight GarvisScore.

        For the full evaluation with alerts and export, use evaluate().
        """
        request = EvalRequest(
            prompt=prompt,
            response=response,
            context=context,
        )
        return self._scorer.score(request)

    def batch_evaluate(
        self, requests: list[EvalRequest]
    ) -> list[EvalResult]:
        """Evaluate a batch of requests.

        For high-throughput async batch evaluation with
        parallel processing, see ARGUS Platform.
        """
        results = []
        for req in requests:
            result = self._scorer.evaluate(req)
            alerts = self._monitor.check(result)
            result.alerts = alerts
            self._export(result)
            results.append(result)
        return results

    @property
    def weights(self) -> GarvisWeights:
        return self._scorer.weights

    @property
    def thresholds(self) -> ThresholdConfig:
        return self._thresholds

    def _init_exporters(self, names: list[str]) -> list[str]:
        """Initialize metrics exporters. Returns list of active ones."""
        active = []
        for name in names:
            if name == "console":
                active.append("console")
            elif name == "prometheus":
                try:
                    from argus_ai.exporters.prometheus import PrometheusExporter
                    self._prom_exporter = PrometheusExporter()
                    active.append("prometheus")
                except ImportError:
                    logger.warning(
                        "prometheus_exporter_unavailable",
                        hint="pip install argus-ai[prometheus]",
                    )
            elif name == "opentelemetry":
                try:
                    from argus_ai.exporters.otel import OtelExporter
                    self._otel_exporter = OtelExporter()
                    active.append("opentelemetry")
                except ImportError:
                    logger.warning(
                        "otel_exporter_unavailable",
                        hint="pip install argus-ai[opentelemetry]",
                    )
        return active

    def _export(self, result: EvalResult) -> None:
        """Export metrics to all configured exporters."""
        flat = result.to_flat_dict()

        if "console" in self._exporters:
            logger.info("garvis_score", **flat)

        if "prometheus" in self._exporters:
            self._prom_exporter.export(result)

        if "opentelemetry" in self._exporters:
            self._otel_exporter.export(result)


def init(
    profile: str = "enterprise",
    weights: GarvisWeights | None = None,
    thresholds: ThresholdConfig | None = None,
    alert_rules: list[AlertRule] | None = None,
    exporters: list[str] | None = None,
    on_alert: Callable[[str, EvalResult], None] | None = None,
) -> ArgusClient:
    """Initialize the ARGUS client.

    This is the recommended entry point:

        import argus_ai
        argus = argus_ai.init()
        result = argus.evaluate(prompt=p, response=r, context=c)

    Args:
        profile: Weight profile name. Options: enterprise, healthcare,
                 finance, consumer, agentic
        weights: Custom GarvisWeights (overrides profile)
        thresholds: Custom threshold configuration
        alert_rules: List of alert rules for monitoring
        exporters: List of exporter names: console, prometheus, opentelemetry
        on_alert: Callback invoked when alerts fire

    Returns:
        Configured ArgusClient instance
    """
    return ArgusClient(
        weights=weights,
        profile=profile,
        thresholds=thresholds,
        alert_rules=alert_rules,
        exporters=exporters,
        on_alert=on_alert,
    )


# Alias for convenience - ArgusEvaluator is equivalent to ArgusClient
ArgusEvaluator = ArgusClient
