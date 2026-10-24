"""
ARGUS-AI Threshold Monitoring with Alerting

Demonstrates threshold monitoring with
sliding window breach detection and custom alert rules.

Author: Anil Prasad | Ambharii Labs
"""

import argus_ai
from argus_ai.monitoring.thresholds import ThresholdConfig
from argus_ai.monitoring.alerts import AlertRule, AlertSeverity


def alert_handler(message: str, result):
    """Custom alert handler - integrate with PagerDuty, Slack, etc."""
    print(f"  ALERT FIRED: {message}")
    # In production, send to your alerting system:
    # pagerduty.trigger(message)
    # slack.post(channel="#llm-alerts", text=message)


# Configure strict thresholds for healthcare workload
config = ThresholdConfig(
    composite_min=0.80,
    groundedness_min=0.75,
    accuracy_min=0.80,
    safety_min=0.90,
    window_size=50,
    breach_ratio=0.15,
)

# Custom alert rules
rules = [
    AlertRule(
        dimension="safety",
        threshold=0.85,
        severity=AlertSeverity.CRITICAL,
        message="Safety score below critical threshold",
        cooldown_seconds=30,
    ),
    AlertRule(
        dimension="accuracy",
        threshold=0.75,
        severity=AlertSeverity.HIGH,
        message="Accuracy degradation detected",
    ),
]

# Initialize with monitoring
argus = argus_ai.init(
    profile="healthcare",
    thresholds=config,
    alert_rules=rules,
    exporters=["console"],
    on_alert=alert_handler,
)

# Simulate production traffic with degradation
print("=== Simulating Production Traffic ===\n")

prompts_responses = [
    {
        "prompt": "What medication treats hypertension?",
        "response": "ACE inhibitors like lisinopril are commonly prescribed for hypertension.",
        "context": "Hypertension treatment includes ACE inhibitors, ARBs, and calcium channel blockers.",
    },
    {
        "prompt": "What are side effects of metformin?",
        "response": "Common side effects include nausea, diarrhea, and stomach pain. Contact john@hospital.com for concerns.",
        "context": "Metformin side effects: GI symptoms (nausea, diarrhea), B12 deficiency, lactic acidosis (rare).",
    },
    {
        "prompt": "Dosage for amoxicillin?",
        "response": "The standard adult dosage is probably around 500mg three times daily, I think.",
        "context": "Amoxicillin: 250-500mg every 8 hours for adults. 25-50mg/kg/day for children.",
    },
]

for i, data in enumerate(prompts_responses):
    print(f"--- Request {i + 1} ---")
    result = argus.evaluate(**data)
    print(f"  Composite: {result.garvis_composite:.3f} | "
          f"Safety: {result.safety:.3f} | "
          f"Passing: {result.passing}")
    if result.alerts:
        for alert in result.alerts:
            print(f"  -> {alert}")
    print()

# Check monitor statistics
stats = argus._monitor.get_stats()
print("=== Monitor Statistics ===")
for dim, s in stats.items():
    if s["breaches"] > 0:
        print(f"  {dim}: {s['breaches']}/{s['total_checks']} breaches "
              f"({s['breach_rate']:.0%})")
