from typing import List, Optional, Dict, Any, AsyncGenerator

from ports.llm import LLMProviderPort, LLMMessage, LLMResponse


class MockLLMAdapter:
    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or ["Mock response"]
        self._call_count = 0
        self._calls: List[Dict[str, Any]] = []

    async def complete(
        self,
        messages: List[LLMMessage],
        model: str = "mock",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        self._calls.append({"messages": messages, "model": model, "tools": tools})
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return LLMResponse(
            content=response_text,
            model=model,
            usage={"input": 10, "output": 20},
            stop_reason="end_turn",
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        model: str = "mock",
        max_tokens: int = 8192,
    ) -> AsyncGenerator[str, None]:
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        yield response_text

    def get_calls(self) -> List[Dict[str, Any]]:
        return self._calls
