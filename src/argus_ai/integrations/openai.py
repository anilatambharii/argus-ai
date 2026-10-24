"""
OpenAI Integration

Drop-in wrapper that instruments OpenAI API calls with
automatic G-ARVIS scoring.

Usage:
    from argus_ai.integrations.openai import InstrumentedOpenAI

    client = InstrumentedOpenAI(argus=argus_ai.init())
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Explain transformers"}],
    )
    print(response._argus_score.garvis_composite)

Requires: pip install "argus-llm[openai]"

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


class InstrumentedCompletions:
    """Wrapper around openai.chat.completions with G-ARVIS scoring."""

    def __init__(
        self,
        original_completions: Any,
        argus: ArgusClient,
        context: str | None = None,
    ) -> None:
        self._completions = original_completions
        self._argus = argus
        self._context = context
        self.last_result: EvalResult | None = None

    def create(self, **kwargs: Any) -> Any:
        """Instrumented completions.create with G-ARVIS evaluation."""
        messages = kwargs.get("messages", [])
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    prompt = content

        model_name = kwargs.get("model", "unknown")

        start = time.perf_counter()
        response = self._completions.create(**kwargs)
        latency_ms = (time.perf_counter() - start) * 1000

        response_text = ""
        input_tokens = None
        output_tokens = None

        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            if hasattr(choice, "message") and hasattr(choice.message, "content"):
                response_text = choice.message.content or ""

        if hasattr(response, "usage") and response.usage:
            input_tokens = getattr(response.usage, "prompt_tokens", None)
            output_tokens = getattr(response.usage, "completion_tokens", None)

        result = self._argus.evaluate(
            prompt=prompt,
            response=response_text,
            context=self._context,
            model_name=model_name,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        response._argus_score = result
        self.last_result = result

        logger.info(
            "openai_call_scored",
            model=model_name,
            composite=result.garvis_composite,
            passing=result.passing,
            latency_ms=round(latency_ms, 1),
        )

        return response


class InstrumentedChat:
    """Wrapper around openai.chat namespace."""

    def __init__(
        self,
        original_chat: Any,
        argus: ArgusClient,
        context: str | None = None,
    ) -> None:
        self.completions = InstrumentedCompletions(
            original_completions=original_chat.completions,
            argus=argus,
            context=context,
        )


class InstrumentedOpenAI:
    """Drop-in replacement for openai.OpenAI with G-ARVIS scoring.

    Usage:
        import argus_ai
        from argus_ai.integrations.openai import InstrumentedOpenAI

        argus = argus_ai.init(profile="consumer")
        client = InstrumentedOpenAI(argus=argus)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello"}]
        )
        print(response._argus_score.garvis_composite)
    """

    def __init__(
        self,
        argus: ArgusClient,
        context: str | None = None,
        **openai_kwargs: Any,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError:
            raise ImportError(
                "openai package required. Install with: "
                "pip install argus-llm[openai]"
            ) from None

        self._client = OpenAI(**openai_kwargs)
        self._argus = argus
        self.chat = InstrumentedChat(
            original_chat=self._client.chat,
            argus=argus,
            context=context,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
