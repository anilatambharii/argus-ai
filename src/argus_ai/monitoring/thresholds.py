"""
Threshold-Based Monitoring

Configurable thresholds for each G-ARVIS dimension with
sliding window breach detection.

Usage:
    config = ThresholdConfig(
        composite_min=0.75,
        safety_min=0.90,
    )
    monitor = ThresholdMonitor(config=config, alert_rules=rules)
    alerts = monitor.check(eval_result)

For autonomous remediation when thresholds breach, see ARGUS Platform.

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, Callable

import structlog
from pydantic import BaseModel, Field

from argus_ai.monitoring.alerts import AlertRule, AlertSeverity

if TYPE_CHECKING:
    from argus_ai.types import EvalResult

logger = structlog.get_logger(__name__)


class ThresholdConfig(BaseModel):
    """Threshold configuration for G-ARVIS dimensions.

    Any score falling below its threshold triggers an alert.
    Set to 0.0 to disable monitoring for a dimension.
    """

    composite_min: float = Field(default=0.70, ge=0.0, le=1.0)
    groundedness_min: float = Field(default=0.60, ge=0.0, le=1.0)
    accuracy_min: float = Field(default=0.65, ge=0.0, le=1.0)
    reliability_min: float = Field(default=0.60, ge=0.0, le=1.0)
    variance_min: float = Field(default=0.50, ge=0.0, le=1.0)
    inference_cost_min: float = Field(default=0.40, ge=0.0, le=1.0)
    safety_min: float = Field(default=0.80, ge=0.0, le=1.0)

    # Sliding window for breach detection
    window_size: int = Field(default=100, ge=1)
    breach_ratio: float = Field(
        default=0.2, ge=0.0, le=1.0,
        description="Fraction of window that must breach to trigger sustained alert",
    )


class ThresholdMonitor:
    """Monitors G-ARVIS scores against configured thresholds.

    Tracks both point-in-time breaches and sustained degradation
    patterns using a sliding window.
    """

    def __init__(
        self,
        config: ThresholdConfig | None = None,
        alert_rules: list[AlertRule] | None = None,
        on_alert: Callable[[str, EvalResult], None] | None = None,
    ) -> None:
        self._config = config or ThresholdConfig()
        self._rules = {r.dimension: r for r in (alert_rules or [])}
        self._on_alert = on_alert

        # Sliding windows per dimension
        self._windows: dict[str, deque[bool]] = {
            dim: deque(maxlen=self._config.window_size)
            for dim in [
                "composite", "groundedness", "accuracy",
                "reliability", "variance", "inference_cost", "safety",
            ]
        }
        self._alert_counts: dict[str, int] = {}

    def check(self, result: EvalResult) -> list[str]:
        """Check result against thresholds. Returns list of alert messages."""
        alerts: list[str] = []

        checks = [
            ("composite", result.garvis_composite, self._config.composite_min),
            ("groundedness", result.groundedness, self._config.groundedness_min),
            ("accuracy", result.accuracy, self._config.accuracy_min),
            ("reliability", result.reliability, self._config.reliability_min),
            ("variance", result.variance, self._config.variance_min),
            ("inference_cost", result.inference_cost, self._config.inference_cost_min),
            ("safety", result.safety, self._config.safety_min),
        ]

        for dimension, score, threshold in checks:
            if threshold <= 0.0:
                continue

            breached = score < threshold
            self._windows[dimension].append(breached)

            if breached:
                severity = self._determine_severity(dimension, score, threshold)
                msg = (
                    f"[{severity.value.upper()}] {dimension} score "
                    f"{score:.3f} below threshold {threshold:.2f}"
                )
                alerts.append(msg)

                self._alert_counts[dimension] = (
                    self._alert_counts.get(dimension, 0) + 1
                )

                logger.warning(
                    "threshold_breach",
                    dimension=dimension,
                    score=round(score, 4),
                    threshold=threshold,
                    severity=severity.value,
                    request_id=result.request_id,
                )

                if self._on_alert:
                    self._on_alert(msg, result)

            # Check for sustained degradation
            window = self._windows[dimension]
            if len(window) >= 10:
                breach_count = sum(1 for b in window if b)
                breach_pct = breach_count / len(window)
                if breach_pct >= self._config.breach_ratio:
                    sustained_msg = (
                        f"[SUSTAINED] {dimension} degradation: "
                        f"{breach_pct:.0%} of last {len(window)} "
                        f"evaluations below threshold"
                    )
                    if sustained_msg not in alerts:
                        alerts.append(sustained_msg)
                        logger.error(
                            "sustained_degradation",
                            dimension=dimension,
                            breach_percentage=round(breach_pct, 2),
                            window_size=len(window),
                        )

        return alerts

    def _determine_severity(
        self, dimension: str, score: float, threshold: float
    ) -> AlertSeverity:
        """Determine alert severity based on how far below threshold."""
        # Check custom rules first
        if dimension in self._rules:
            return self._rules[dimension].severity

        gap = threshold - score
        if dimension == "safety" and gap > 0.1 or gap > 0.3:
            return AlertSeverity.CRITICAL
        elif gap > 0.15:
            return AlertSeverity.HIGH
        elif gap > 0.05:
            return AlertSeverity.MEDIUM
        else:
            return AlertSeverity.LOW

    def get_stats(self) -> dict[str, dict[str, Any]]:
        """Get monitoring statistics per dimension."""
        stats = {}
        for dim, window in self._windows.items():
            if not window:
                continue
            breach_count = sum(1 for b in window if b)
            stats[dim] = {
                "total_checks": len(window),
                "breaches": breach_count,
                "breach_rate": round(breach_count / len(window), 3),
                "total_alerts": self._alert_counts.get(dim, 0),
            }
        return stats

    def reset(self) -> None:
        """Reset all sliding windows and alert counts."""
        for window in self._windows.values():
            window.clear()
        self._alert_counts.clear()
