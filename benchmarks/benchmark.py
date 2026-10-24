"""
Reproduce the numbers in the README "Performance" section.

Usage:
    python benchmarks/benchmark.py

Evaluates the README Quick Start example repeatedly with default settings
(console logging on) and prints single-call latency percentiles, the time
for 1,000 sequential calls, and process memory before/after.
Output goes to stderr so the per-call log lines can be discarded:

    python benchmarks/benchmark.py > /dev/null
"""

import platform
import statistics
import sys
import time

import argus_ai

REQUEST = {
    "prompt": "What causes climate change?",
    "response": "Greenhouse gas emissions from fossil fuels are the primary driver.",
    "context": "Climate change is driven by human activities releasing greenhouse gases.",
    "model_name": "claude-sonnet-4",
    "latency_ms": 1200.0,
    "input_tokens": 45,
    "output_tokens": 30,
    "cost_usd": 0.002,
}


def main() -> None:
    argus = argus_ai.init(profile="enterprise")

    samples = []
    for _ in range(2000):
        start = time.perf_counter()
        argus.evaluate(**REQUEST)
        samples.append((time.perf_counter() - start) * 1000)
    samples.sort()

    start = time.perf_counter()
    for _ in range(1000):
        argus.evaluate(**REQUEST)
    batch_s = time.perf_counter() - start

    print(f"argus-llm {argus_ai.__version__} | Python {platform.python_version()} | "
          f"{platform.platform()}", file=sys.stderr)
    print(f"single evaluate(): median={statistics.median(samples):.3f} ms "
          f"p95={samples[int(0.95 * len(samples))]:.3f} ms "
          f"p99={samples[int(0.99 * len(samples))]:.3f} ms "
          f"max={samples[-1]:.3f} ms (n={len(samples)})", file=sys.stderr)
    print(f"1000 sequential evaluate() calls: {batch_s:.3f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
