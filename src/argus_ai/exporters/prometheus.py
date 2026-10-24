"""
Prometheus Metrics Exporter

Exposes G-ARVIS scores as Prometheus gauges and histograms
for Grafana dashboard consumption.

Requires: pip install "argus-llm[prometheus]"

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram, Info

from argus_ai import __version__

if TYPE_CHECKING:
    from argus_ai.types import EvalResult


class PrometheusExporter:
    """Exports G-ARVIS metrics to Prometheus."""

    def __init__(self, prefix: str = "argus") -> None:
        self._prefix = prefix

        # Info metric
        self._info = Info(
            f"{prefix}_build",
            "ARGUS AI build information",
        )
        self._info.info({"version": __version__, "framework": "garvis"})

        # Composite score gauge
        self._composite = Gauge(
            f"{prefix}_garvis_composite",
            "G-ARVIS composite score",
            ["model"],
        )

        # Per-dimension gauges
        self._dimensions: dict[str, Gauge] = {}
        for dim in [
            "groundedness", "accuracy", "reliability",
            "variance", "inference_cost", "safety",
        ]:
            self._dimensions[dim] = Gauge(
                f"{prefix}_garvis_{dim}",
                f"G-ARVIS {dim} score",
                ["model"],
            )

        # Evaluation latency histogram
        self._eval_duration = Histogram(
            f"{prefix}_evaluation_duration_ms",
            "G-ARVIS evaluation duration in milliseconds",
            ["model"],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500],
        )

        # Alert counter
        self._alerts = Counter(
            f"{prefix}_alerts_total",
            "Total G-ARVIS threshold alerts",
            ["dimension", "severity"],
        )

        # Evaluation counter
        self._eval_total = Counter(
            f"{prefix}_evaluations_total",
            "Total G-ARVIS evaluations",
            ["model", "passing"],
        )

    def export(self, result: EvalResult) -> None:
        """Export a single evaluation result to Prometheus metrics."""
        model = "unknown"
        # Try to extract model from details
        for detail in result.metric_details:
            if detail.details.get("model_name"):
                model = detail.details["model_name"]
                break

        self._composite.labels(model=model).set(result.garvis_composite)

        dim_map = {
            "groundedness": result.groundedness,
            "accuracy": result.accuracy,
            "reliability": result.reliability,
            "variance": result.variance,
            "inference_cost": result.inference_cost,
            "safety": result.safety,
        }
        for dim, score in dim_map.items():
            self._dimensions[dim].labels(model=model).set(score)

        self._eval_duration.labels(model=model).observe(result.evaluation_ms)
        self._eval_total.labels(
            model=model,
            passing=str(result.passing).lower(),
        ).inc()

        # Count alerts
        for alert_msg in result.alerts:
            severity = "medium"
            for sev in ["critical", "high", "medium", "low"]:
                if sev.upper() in alert_msg:
                    severity = sev
                    break
            dimension = "unknown"
            for dim in dim_map:
                if dim in alert_msg.lower():
                    dimension = dim
                    break
            self._alerts.labels(
                dimension=dimension,
                severity=severity,
            ).inc()
