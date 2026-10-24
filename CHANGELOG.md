# Changelog

All notable changes to argus-ai will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-10-23

Mostly a metadata and documentation release. No scoring behavior changed.

### Fixed

- `import argus_ai` raised `TypeError` on Python 3.9 (pydantic cannot evaluate `X | None` there), although 0.1.0 declares support for 3.9. The model fields in `types.py` now use `Optional[X]`. CI now passes on 3.9 through 3.13.
- Lint (`ruff`) and type-check (`mypy`) errors that kept CI red; no behavior changes.
- README, docstrings, error hints, and example comments told users to run `pip install argus-ai`, which installs an unrelated PyPI package. The correct command is `pip install argus-llm` (extras: `argus-llm[anthropic]`, `[openai]`, `[prometheus]`, `[opentelemetry]`, `[all]`). The import name is unchanged: `import argus_ai`.
- The PyPI badge in the README now points at `argus-llm`.
- The Prometheus `argus_build_info` metric now reports the package's real `__version__` instead of a hardcoded `0.1.0`.
- README example outputs now show the real output of the snippets (Quick Start composite 0.755 and safety 1.000, previously shown as 0.847 and 0.950; agentic ASF/ERR 0.632/0.540, previously 0.612/0.600).
- README formulas for ERR and CPCS now match the implementation.

### Changed

- Removed "SOC2/HIPAA Compliance" from the README's commercial-platform column and from ARCHITECTURE.md. This library does not provide or certify regulatory compliance; the `healthcare` and `finance` weight profiles only change dimension weights. The README now says so.
- The commercial ARGUS Platform column is labelled as planned and not part of this package.
- Removed "production-grade" wording from the README, package description, and docstrings; the package is Beta (0.1.x).
- Described the scorers as heuristics (word overlap, regex, keyword lists) rather than as detecting hallucinations, toxicity, or PII. Removed the unsupported "12% more hallucination" example and the vendor-compatibility list for the OpenTelemetry exporter.
- Replaced the unmeasured performance table with measured numbers and the script to reproduce them (`benchmarks/benchmark.py`). Removed the "< 5MB memory" and "zero external dependencies" claims.
- Removed the dead `Documentation` project URL (`argus-ai.ambharii.com` does not respond) and the `ai-safety` and `guardrails` keywords.

### Added

- `benchmarks/benchmark.py` to reproduce the README performance numbers.

## [0.1.0] - 2026-03-17

### Added

- G-ARVIS composite scoring engine with 6 dimensions (Groundedness, Accuracy, Reliability, Variance, Inference Cost, Safety)
- 3-line SDK client with `argus_ai.init()` entry point
- Agentic evaluation metrics: ASF (Agent Stability Factor), ERR (Error Recovery Rate), CPCS (Cost Per Completed Step)
- 5 pre-built weight profiles: enterprise, healthcare, finance, consumer, agentic
- Threshold monitoring with sliding window breach detection
- Alert rules with severity levels and custom callbacks
- Prometheus metrics exporter
- OpenTelemetry metrics exporter
- Anthropic Claude drop-in wrapper (`InstrumentedAnthropic`)
- OpenAI drop-in wrapper (`InstrumentedOpenAI`)
- Decorator-based instrumentation (`@argus_evaluate`)
- Full type annotations with mypy strict mode
- CI/CD pipeline with GitHub Actions
- Apache 2.0 license
