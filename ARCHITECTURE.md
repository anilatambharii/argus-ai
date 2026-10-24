# ARGUS-AI Architecture

## Open Core Strategy

ARGUS follows an **Open Core** model. This repository is the open-source layer.
The "ARGUS Platform" layer shown below is planned and is not part of this package or available today.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        ARGUS Platform (Commercial)                   │
│                                                                      │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  Orchestrator    │ │  Prompt Optimizer │ │  Self-Healing Loop   │  │
│  │  Agent           │ │  (Auto-tune)     │ │  (Closed-Loop)       │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  LLM-as-Judge   │ │  Async Batch     │ │  Multi-Model         │  │
│  │  Evaluation     │ │  Processing      │ │  Variance Analysis   │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  Dashboard UI   │ │  Team Management │ │  Audit Reporting     │  │
│  │                 │ │                  │ │  (planned)           │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                    argus-ai (Open Source - This Repo)                 │
│                                                                      │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  G-ARVIS Scorer │ │  3-Line SDK      │ │  Threshold Monitor   │  │
│  │  (6 Dimensions) │ │  init/evaluate   │ │  + Sliding Window    │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────┘  │
│  ┌─────────────────┐ ┌──────────────────┐ ┌──────────────────────┐  │
│  │  Agentic Metrics│ │  Exporters       │ │  Provider Wrappers   │  │
│  │  ASF/ERR/CPCS   │ │  Prom/OTEL/CLI   │ │  Anthropic/OpenAI    │  │
│  └─────────────────┘ └──────────────────┘ └──────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User LLM Call
     │
     ▼
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  ArgusClient │────▶│              GarvisScorer                    │
│  .evaluate() │     │                                              │
└─────────────┘     │  ┌───────────┐ ┌──────────┐ ┌───────────┐   │
                    │  │Groundednes│ │ Accuracy │ │Reliability│   │
                    │  │  Scorer   │ │  Scorer  │ │  Scorer   │   │
                    │  └─────┬─────┘ └────┬─────┘ └─────┬─────┘   │
                    │  ┌─────┴─────┐ ┌────┴─────┐ ┌─────┴─────┐   │
                    │  │ Variance  │ │Inference │ │  Safety   │   │
                    │  │  Scorer   │ │CostScorer│ │  Scorer   │   │
                    │  └─────┬─────┘ └────┬─────┘ └─────┬─────┘   │
                    │        └────────┬────┘             │         │
                    │                 ▼                   │         │
                    │        Weighted Composite ◄────────┘         │
                    └──────────────────┬───────────────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────────┐
                    │         ThresholdMonitor              │
                    │  ┌────────────┐  ┌────────────────┐  │
                    │  │ Point-in-  │  │  Sliding Window │  │
                    │  │ Time Check │  │  Breach Detect  │  │
                    │  └──────┬─────┘  └───────┬────────┘  │
                    │         └──────┬─────────┘           │
                    │                ▼                      │
                    │           Alert Rules                 │
                    └────────────────┬─────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
              ┌──────────┐  ┌──────────────┐  ┌────────────┐
              │ Console  │  │ Prometheus   │  │ OpenTelemetry│
              │ Exporter │  │ Exporter     │  │ Exporter    │
              └──────────┘  └──────────────┘  └────────────┘
```

## Module Structure

```
src/argus_ai/
├── __init__.py              # Public API surface (3-line SDK)
├── types.py                 # Pydantic data models
├── scoring/
│   ├── garvis.py            # Composite scorer + weight profiles
│   ├── metrics.py           # 6 individual dimension scorers
│   └── agentic.py           # ASF, ERR, CPCS metrics
├── sdk/
│   ├── client.py            # ArgusClient + init()
│   └── decorators.py        # @argus_evaluate decorator
├── monitoring/
│   ├── thresholds.py        # ThresholdMonitor + sliding window
│   └── alerts.py            # AlertRule + severity definitions
├── exporters/
│   ├── prometheus.py        # Prometheus gauges/histograms
│   └── otel.py              # OpenTelemetry metrics
└── integrations/
    ├── anthropic.py         # InstrumentedAnthropic wrapper
    └── openai.py            # InstrumentedOpenAI wrapper
```

## Design Principles

1. **Small core**: Only pydantic, numpy, structlog are required (exporters and provider wrappers are optional extras)
2. **Lightweight scoring**: Heuristic scorers; roughly 0.6 ms median per evaluation in the README benchmark (see `benchmarks/benchmark.py`)
3. **Extensible**: Scorers and exporters are plain classes; a formal plugin API is on the roadmap
4. **Type-safe**: Full mypy strict mode compliance
5. **Production-first**: Structured logging, Prometheus/OTEL export, alert callbacks

## What's NOT in Open Source (ARGUS Platform)

The following capabilities are planned for the commercial platform and are not included in this package:

- **Autonomous correction loop**: The orchestrator agent that automatically
  fixes degraded LLM outputs
- **Prompt optimizer**: Auto-tunes prompts based on G-ARVIS score trends
- **LLM-as-judge evaluation**: Model-based quality scoring (vs heuristic)
- **Multi-run variance analysis**: Temperature sweep, prompt perturbation tests
- **Async batch processing**: High-throughput parallel evaluation pipeline
- **Dashboard UI**: Real-time G-ARVIS visualization and team management
- **Audit-trail reporting** (planned)
