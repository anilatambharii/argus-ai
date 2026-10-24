# Field Notes: Production AI — Edition 4

## We Open-Sourced the Scoring Engine. We Kept the Self-Healing Loop.

Today I am releasing argus-ai to the world.

`pip install argus-llm`

Three lines of code. Every LLM call in your application now has a quality score.

```python
import argus_ai
argus = argus_ai.init()
result = argus.evaluate(prompt=prompt, response=response, context=context)
```

Here is what that score tells you.

---

### The Problem Nobody Is Measuring

Your LLM application is degrading right now. You cannot see it because you are not measuring it.

Traditional observability catches latency spikes, error rates, and throughput drops. It does not catch a model that starts hallucinating 12% more after a provider update. It does not catch a prompt that silently loses grounding when context exceeds 80K tokens. It does not catch cost creep from token bloat that accumulates over weeks.

I have watched this happen across every production LLM deployment I have worked on. At Duke Energy. At UnitedHealth Group. At R1 RCM. The pattern is always the same: the app works great at launch, then quietly degrades while traditional metrics show green across the board.

---

### G-ARVIS: Six Dimensions of LLM Quality

The G-ARVIS framework evaluates every LLM response across six orthogonal quality dimensions:

**G** Groundedness. Is the response anchored in provided context or is it fabricating?

**A** Accuracy. Does it match ground truth? Is it internally consistent? Are numeric claims valid?

**R** Reliability. Is the format consistent? Is it complete or truncated? Does latency meet SLA?

**V** Variance. How deterministic is the output? How confident? How stable across similar inputs?

**I** Inference Cost. Are tokens being used efficiently? Is cost proportionate to value delivered?

**S** Safety. PII leakage? Toxicity? Prompt injection? Harmful content?

Each dimension produces a 0-to-1 score. The weighted composite tells you, in a single number, whether your LLM is performing at production grade.

---

### What Is New: Agentic Evaluation Metrics

In Edition 3 of this newsletter I introduced three metrics that address the evaluation gap for autonomous agent workflows. They are now part of argus-ai.

**ASF** Agent Stability Factor. Completion rate multiplied by failure resilience multiplied by retry consistency. Measures whether your agent reliably finishes what it starts.

**ERR** Error Recovery Rate. Recovered steps divided by failed steps. Measures whether your agent self-corrects or cascades failures.

**CPCS** Cost Per Completed Step. Total spend normalized against successfully completed workflow steps. Measures economic efficiency of autonomous execution.

These are the metrics that traditional LLM evaluation frameworks do not have. BLEU, ROUGE, perplexity were designed for static text generation. They tell you nothing about whether a 10-step agent workflow will survive its third tool call failure and still deliver the result.

---

### Why Open Source

I built ARGUS as a full platform: scoring, monitoring, autonomous correction, and self-healing. The question was always which layers to open.

The answer is the layer that creates dependency.

argus-ai gives you the G-ARVIS scoring engine, threshold monitoring with sliding window breach detection, Prometheus and OpenTelemetry export, and drop-in wrappers for Anthropic and OpenAI. Install it, plug it into your LLM pipeline, and suddenly you can see the degradation you could not see before.

What it does not give you is the fix. Detection without correction is a dashboard you stare at while your app degrades. The autonomous correction loop, the prompt optimizer, the closed-loop self-healing pipeline: that is ARGUS Platform. That is where the road leads.

---

### The Numbers

Sub-5ms evaluation latency. 84 unit tests. 93% code coverage on the scoring core. Three runtime dependencies. Five pre-built weight profiles for enterprise, healthcare, finance, consumer, and agentic workloads. Prometheus and OTEL export out of the box. Python 3.9 through 3.13.

The package is on PyPI today. The repo is at github.com/anilatambharii/argus-ai.

---

### Try It

```bash
pip install argus-llm
```

```python
import argus_ai

argus = argus_ai.init(profile="enterprise")

result = argus.evaluate(
    prompt="What are the Q3 revenue trends?",
    response="Revenue increased 12% year-over-year to $4.2B...",
    context="Q3 2024 financial report data...",
    model_name="claude-sonnet-4",
    latency_ms=1200.0,
)

print(result.garvis_composite)   # 0.847
print(result.passing)            # True
```

If you are running LLMs in production, you need this. Not because I built it. Because your app is degrading and you cannot see it yet.

Star the repo. File issues. Contribute scorers and exporters. This is the foundation.

The self-healing loop comes next.

Anil Prasad
Head of Engineering and Product
Ambharii Labs

github.com/anilatambharii/argus-ai
anilsprasad.com | ambharii.com

#HumanWritten #ProductionAI #LLMOps #OpenSource #GARVIS #ARGUS
