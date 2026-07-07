import os
from typing import Optional, List, Dict, Any, AsyncGenerator

import anthropic

from ports.llm import LLMProviderPort, LLMMessage, LLMResponse


class AnthropicAdapter:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        base_url = base_url or os.getenv("CLAUDE_PROXY_BASE_URL")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)

    async def complete(
        self,
        messages: List[LLMMessage],
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if tools:
            kwargs["tools"] = tools
        response = self._client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
            stop_reason=response.stop_reason,
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8192,
    ) -> AsyncGenerator[str, None]:
        with self._client.messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        ) as stream:
            for text in stream.text_stream:
                yield text
