"""
Decorator-Based LLM Instrumentation

Zero-friction G-ARVIS scoring via Python decorators:

    @argus_evaluate(argus_client)
    def my_llm_call(prompt: str) -> str:
        return call_llm(prompt)

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

import functools
import time
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import structlog

if TYPE_CHECKING:
    from argus_ai.sdk.client import ArgusClient

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def argus_evaluate(
    client: ArgusClient,
    context: str | None = None,
    model_name: str | None = None,
) -> Callable[[F], F]:
    """Decorator that wraps an LLM call with G-ARVIS evaluation.

    The decorated function must accept a `prompt` keyword argument
    (or first positional arg) and return the LLM response string.

    Usage:
        argus = argus_ai.init()

        @argus_evaluate(argus, model_name="claude-sonnet-4")
        def generate(prompt: str) -> str:
            return anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text

        # Result includes both the response and G-ARVIS score
        response = generate("Explain quantum computing")
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract prompt from args
            prompt = kwargs.get("prompt") or (args[0] if args else "")

            # Time the LLM call
            start = time.perf_counter()
            response = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            # Run G-ARVIS evaluation
            response_text = str(response)
            result = client.evaluate(
                prompt=str(prompt),
                response=response_text,
                context=context,
                model_name=model_name,
                latency_ms=latency_ms,
            )

            # Attach score to response if possible
            if hasattr(response, "__dict__"):
                response._argus_result = result

            logger.debug(
                "argus_decorator_eval",
                function=func.__name__,
                composite=result.garvis_composite,
                latency_ms=round(latency_ms, 1),
            )

            return response

        # Expose result accessor
        wrapper.last_result = None  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
