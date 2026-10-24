# ARGUS-AI

**Heuristic quality scoring and monitoring for LLM outputs, in 3 lines of code**

[![PyPI version](https://img.shields.io/pypi/v/argus-llm.svg)](https://pypi.org/project/argus-llm/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI](https://github.com/anilatambharii/argus-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/anilatambharii/argus-ai/actions)

ARGUS-AI is the **G-ARVIS scoring engine** for monitoring LLM application quality. It scores each LLM response across six dimensions: **G**roundedness, **A**ccuracy, **R**eliability, **V**ariance, **I**nference Cost, and **S**afety.

> **Status: Beta (0.1.x).** All scorers are lightweight rule-based heuristics (keyword, regex, and token-overlap checks), not trained models. Treat the scores as trend signals to monitor over time, not as verdicts on any single response. This repository does not include benchmarks of the scorers against labelled datasets.

```python
import argus_ai

argus = argus_ai.init()
result = argus.evaluate(prompt=prompt, response=response, context=context)
```

That's it. Every LLM call you pass through `evaluate` gets a G-ARVIS score.

---

## Why ARGUS

LLM outputs can degrade without raising errors: models update, prompts drift, and costs creep. Traditional monitoring catches latency and errors, but not changes in output quality. G-ARVIS gives you per-dimension scores you can export to your metrics stack and alert on, so a drop shows up in a dashboard instead of in a user complaint.

| Dimension | What the heuristic measures | Signal for |
|-----------|-----------------------------|------------|
| **Groundedness** | Word overlap between the response and the context you supply (plus small adjustments for attribution and speculation phrases). Returns a neutral 0.5 when no context is given. | Responses drifting away from the provided context. Not a hallucination detector. |
| **Accuracy** | Token-level F1 against `ground_truth` when you supply it, plus simple internal-consistency and numeric checks | Obvious mismatches with a reference answer. Does not verify facts. |
| **Reliability** | Truncation markers, JSON/markdown format checks, response length relative to the prompt, latency tiers | Structural quality |
| **Variance** | Wording signals in a single response (hedging vs. definitive phrases, vocabulary diversity). Multi-run variance analysis is not part of this package. | Confidence and consistency of tone |
| **Inference Cost** | Token, cost, and latency ratios computed from the numbers you pass in | Budget control |
| **Safety** | Regex and keyword scan of the response for PII-like patterns (emails, SSNs, card and phone numbers), a short toxicity word list, and system-prompt/jailbreak marker phrases | Flagging risky-looking output. It will miss things and produce false positives; it does not replace dedicated safety or security tooling. |

Plus three **agentic evaluation metrics** for autonomous workflows (scores in [0, 1]; see `src/argus_ai/scoring/agentic.py` for the exact formulas):

| Metric | Formula (simplified) | What It Measures |
|--------|---------|-----------------|
| **ASF** (Agent Stability Factor) | completion_ratio × (1 - failure_rate) × consistency_factor (a retry penalty) | Workflow completion reliability |
| **ERR** (Error Recovery Rate) | recovered / failed, plus a small bonus for fewer retries per recovery | Recovery from failed steps |
| **CPCS** (Cost Per Completed Step) | 1 - min((total_cost / completed_steps) / budget_per_step, 1), default budget $0.10/step | Cost efficiency per step |

---

## Install

```bash
pip install argus-llm
```

The PyPI package is named `argus-llm`; the Python import name is `argus_ai`. (The similarly named `argus-ai` package on PyPI is an unrelated project.)

With provider integrations:

```bash
pip install "argus-llm[anthropic]"      # Anthropic Claude wrapper
pip install "argus-llm[openai]"         # OpenAI wrapper
pip install "argus-llm[prometheus]"     # Prometheus export
pip install "argus-llm[opentelemetry]"  # OTEL export
pip install "argus-llm[all]"            # Everything
```

---

## Quick Start

### Basic Evaluation

```python
import argus_ai

argus = argus_ai.init(profile="enterprise")

result = argus.evaluate(
    prompt="What causes climate change?",
    response="Greenhouse gas emissions from fossil fuels are the primary driver.",
    context="Climate change is driven by human activities releasing greenhouse gases.",
    model_name="claude-sonnet-4",
    latency_ms=1200.0,
    input_tokens=45,
    output_tokens=30,
    cost_usd=0.002,
)

print(f"Composite: {result.garvis_composite:.3f}")  # 0.755
print(f"Passing:   {result.passing}")                # True
print(f"Safety:    {result.safety:.3f}")             # 1.000
```

The values in the comments are the actual output of this snippet on argus-llm 0.1.1. Scores depend on your inputs and the heuristics, and may change between releases. (Here the groundedness score is low, 0.167, because the response shares few words with the context; the heuristic measures word overlap, not meaning.)

### Agentic Workflow Evaluation

```python
from argus_ai.types import AgenticEvalRequest

argus = argus_ai.init(profile="agentic")

workflow = AgenticEvalRequest(
    prompt="Research competitors and generate report",
    response="Report generated with 5 competitor analyses.",
    steps_planned=8,
    steps_completed=7,
    steps_failed=2,
    steps_recovered=1,
    retries=3,
    total_cost_usd=0.45,
)

result, agentic_metrics = argus.evaluate_agentic(workflow)

for m in agentic_metrics:
    print(f"{m.name}: {m.score:.3f}")
# AgentStabilityFactor: 0.632
# ErrorRecoveryRate: 0.540
# CostPerCompletedStep: 0.357
```

(Actual output on argus-llm 0.1.1.)

### Drop-In Provider Wrappers

**Anthropic Claude:**

```python
from argus_ai.integrations.anthropic import InstrumentedAnthropic

argus = argus_ai.init()
client = InstrumentedAnthropic(argus=argus)

response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain transformers"}],
)

# G-ARVIS score automatically attached
print(response._argus_score.garvis_composite)
```

**OpenAI:**

```python
from argus_ai.integrations.openai import InstrumentedOpenAI

client = InstrumentedOpenAI(argus=argus_ai.init())

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Explain transformers"}],
)

print(response._argus_score.garvis_composite)
```

### Threshold Monitoring with Alerting

```python
from argus_ai.monitoring.thresholds import ThresholdConfig
from argus_ai.monitoring.alerts import AlertRule, AlertSeverity

config = ThresholdConfig(
    composite_min=0.80,
    safety_min=0.90,
    window_size=100,
    breach_ratio=0.15,
)

rules = [
    AlertRule(
        dimension="safety",
        threshold=0.85,
        severity=AlertSeverity.CRITICAL,
        message="Safety below critical threshold",
    ),
]

argus = argus_ai.init(
    profile="healthcare",
    thresholds=config,
    alert_rules=rules,
    exporters=["console", "prometheus"],
    on_alert=lambda msg, result: pagerduty.trigger(msg),
)
```

### Decorator Instrumentation

```python
from argus_ai.sdk.decorators import argus_evaluate

argus = argus_ai.init()

@argus_evaluate(argus, model_name="claude-sonnet-4")
def generate(prompt: str) -> str:
    return anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": prompt}]
    ).content[0].text
```

---

## Weight Profiles

G-ARVIS weights are configurable per deployment scenario:

| Profile | G | A | R | V | I | S | Best For |
|---------|---|---|---|---|---|---|----------|
| `enterprise` | 0.20 | 0.20 | 0.15 | 0.15 | 0.10 | 0.20 | General production |
| `healthcare` | 0.25 | 0.25 | 0.15 | 0.10 | 0.05 | 0.20 | Healthcare-oriented weights |
| `finance` | 0.20 | 0.25 | 0.20 | 0.10 | 0.05 | 0.20 | Finance-oriented weights |
| `consumer` | 0.15 | 0.15 | 0.20 | 0.15 | 0.20 | 0.15 | Cost-sensitive apps |
| `agentic` | 0.15 | 0.15 | 0.25 | 0.20 | 0.10 | 0.15 | Autonomous agents |

These profiles only change how the six dimension scores are weighted into the composite. This library scores LLM outputs and does not provide or certify regulatory compliance.

Custom weights:

```python
from argus_ai.scoring.garvis import GarvisWeights

argus = argus_ai.init(weights=GarvisWeights(safety=0.40, accuracy=0.30))
```

---

## Metrics Export

### Prometheus

```python
argus = argus_ai.init(exporters=["prometheus"])
```

Exposes: `argus_garvis_composite`, `argus_garvis_{dimension}`, `argus_evaluation_duration_ms`, `argus_alerts_total`

### OpenTelemetry

```python
argus = argus_ai.init(exporters=["opentelemetry"])
```

Emits metrics through the OpenTelemetry API, so they flow to whatever exporter you configure in the OpenTelemetry SDK (for example OTLP). It has not been tested against specific vendor backends.

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design and open core split.

```
argus-ai (this package, Apache-2.0)   ARGUS Platform (planned; NOT part of
                                      this package and not available)
├── G-ARVIS heuristic scorers         ├── Autonomous Correction Loop
├── 3-Line SDK                        ├── Prompt Optimizer
├── Threshold Monitor                 ├── LLM-as-Judge Evaluation
├── ASF/ERR/CPCS Metrics              ├── Multi-Run Variance Analysis
├── Prometheus/OTEL Export            └── Dashboard UI
└── Anthropic/OpenAI Wrappers
```

Nothing in the right-hand column is included in, or can be obtained through, this package.

---

## Performance

G-ARVIS scoring is pure Python (regex and string operations) with no network calls. Measured on one machine (Intel Xeon E3-1505M v6 @ 3.0 GHz, 64 GB RAM, Windows 10, Python 3.11, argus-llm 0.1.1, default console logging on, evaluating the Quick Start example repeatedly):

| Measurement | Result |
|-------------|--------|
| Single `evaluate()` call | median ≈ 0.6 ms, p99 ≈ 2.6 ms (3.7 ms worst of 2,000 calls) |
| 1,000 sequential `evaluate()` calls | ≈ 0.6 s |
| Memory | No measurable growth over 1,000 calls. Importing the package and its dependencies adds about 19 MB of process memory. |
| Core install dependencies | 3 (pydantic, numpy, structlog), as declared in `pyproject.toml` |

Your numbers will vary with hardware, input length, and logging configuration. Reproduce the timings with `python benchmarks/benchmark.py > /dev/null` (the memory figure was measured separately by comparing process RSS before and after import and after 1,000 calls).

---

## Roadmap

- [ ] LiteLLM integration
- [ ] LangChain callback handler
- [ ] Grafana dashboard templates
- [ ] Custom scorer plugin API
- [ ] Async evaluation support
- [ ] CLI tool for offline batch scoring

---

## Contributing

Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
git clone https://github.com/anilatambharii/argus-ai.git
cd argus-ai
pip install -e ".[dev]"
pytest tests/ -v
```

---

## About

Built by [Anil Prasad](https://anilsprasad.com) at [Ambharii Labs](https://ambharii.com).

G-ARVIS framework published in ["Field Notes: Production AI"](https://www.linkedin.com/newsletters/field-notes-production-ai) on LinkedIn.

ARGUS: Autonomous Runtime Guardian for Unified Systems.

---

## License

Apache 2.0. See [LICENSE](LICENSE).
