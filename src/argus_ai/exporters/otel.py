"""
OpenTelemetry Metrics Exporter

Exports G-ARVIS scores as OTEL metrics for integration with
Datadog, New Relic, Honeycomb, Grafana Cloud, and other
OTLP-compatible backends.

Requires: pip install "argus-llm[opentelemetry]"

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from opentelemetry import metrics

if TYPE_CHECKING:
    from argus_ai.types import EvalResult


class OtelExporter:
    """Exports G-ARVIS metrics via OpenTelemetry."""

    def __init__(self, meter_name: str = "argus.ai") -> None:
        self._meter = metrics.get_meter(meter_name)

        self._composite_gauge = self._meter.create_gauge(
            name="argus.garvis.composite",
            description="G-ARVIS composite score",
            unit="score",
        )

        self._dimension_gauges: dict[str, metrics.Gauge] = {}
        for dim in [
            "groundedness", "accuracy", "reliability",
            "variance", "inference_cost", "safety",
        ]:
            self._dimension_gauges[dim] = self._meter.create_gauge(
                name=f"argus.garvis.{dim}",
                description=f"G-ARVIS {dim} score",
                unit="score",
            )

        self._eval_histogram = self._meter.create_histogram(
            name="argus.evaluation.duration",
            description="Evaluation duration",
            unit="ms",
        )

        self._alert_counter = self._meter.create_counter(
            name="argus.alerts.total",
            description="Total threshold alerts",
        )

    def export(self, result: EvalResult) -> None:
        """Export evaluation result as OTEL metrics."""
        attrs = {"request_id": result.request_id}

        self._composite_gauge.set(result.garvis_composite, attrs)

        dim_map = {
            "groundedness": result.groundedness,
            "accuracy": result.accuracy,
            "reliability": result.reliability,
            "variance": result.variance,
            "inference_cost": result.inference_cost,
            "safety": result.safety,
        }
        for dim, score in dim_map.items():
            self._dimension_gauges[dim].set(score, {**attrs, "dimension": dim})

        self._eval_histogram.record(result.evaluation_ms, attrs)

        for alert in result.alerts:
            self._alert_counter.add(1, {**attrs, "alert": alert[:100]})
