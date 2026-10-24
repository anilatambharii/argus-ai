"""
Anthropic Claude Integration

Drop-in wrapper that instruments Anthropic API calls with
automatic G-ARVIS scoring.

Usage:
    from argus_ai.integrations.anthropic import InstrumentedAnthropic

    client = InstrumentedAnthropic(argus=argus_ai.init())
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Explain transformers"}],
    )
    # response._argus_score is automatically attached

Requires: pip install "argus-llm[anthropic]"

Author: Anil Prasad | Ambharii Labs
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from argus_ai.sdk.client import ArgusClient
    from argus_ai.types import EvalResult

logger = structlog.get_logger(__name__)


class InstrumentedMessages:
    """Wrapper around anthropic.messages that adds G-ARVIS scoring."""

    def __init__(
        self,
        original_messages: Any,
        argus: ArgusClient,
        context: str | None = None,
    ) -> None:
        self._messages = original_messages
        self._argus = argus
        self._context = context
        self.last_result: EvalResult | None = None

    def create(self, **kwargs: Any) -> Any:
        """Instrumented messages.create with G-ARVIS evaluation."""
        # Extract prompt from messages
        messages = kwargs.get("messages", [])
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt = content
                elif isinstance(content, list):
                    prompt = " ".join(
                        block.get("text", "")
                        for block in content
                        if block.get("type") == "text"
                    )

        model_name = kwargs.get("model", "unknown")

        # Time the API call
        start = time.perf_counter()
        response = self._messages.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        # Extract response text
        response_text = ""
        if hasattr(response, "content"):
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

        # Extract token usage
        input_tokens = None
        output_tokens = None
        if hasattr(response, "usage"):
            input_tokens = getattr(response.usage, "input_tokens", None)
            output_tokens = getattr(response.usage, "output_tokens", None)

        # Run G-ARVIS evaluation
        result = self._argus.evaluate(
            prompt=prompt,
            response=response_text,
            context=self._context,
            model_name=model_name,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Attach result to response
        response._argus_score = result
        self.last_result = result

        logger.info(
            "anthropic_call_scored",
            model=model_name,
            composite=result.garvis_composite,
            passing=result.passing,
            latency_ms=round(latency_ms, 1),
        )

        return response


class InstrumentedAnthropic:
    """Drop-in replacement for anthropic.Anthropic with G-ARVIS scoring.

    Usage:
        import argus_ai
        from argus_ai.integrations.anthropic import InstrumentedAnthropic

        argus = argus_ai.init(profile="enterprise")
        client = InstrumentedAnthropic(argus=argus)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello"}]
        )

        print(response._argus_score.garvis_composite)
    """

    def __init__(
        self,
        argus: ArgusClient,
        context: str | None = None,
        **anthropic_kwargs: Any,
    ) -> None:
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: "
                "pip install argus-llm[anthropic]"
            ) from None

        self._client = Anthropic(**anthropic_kwargs)
        self._argus = argus
        self.messages = InstrumentedMessages(
            original_messages=self._client.messages,
            argus=argus,
            context=context,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy all other attributes to the underlying Anthropic client."""
        return getattr(self._client, name)
