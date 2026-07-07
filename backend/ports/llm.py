from typing import Protocol, Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    stop_reason: Optional[str]


class LLMProviderPort(Protocol):
    async def complete(
        self,
        messages: List[LLMMessage],
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse: ...

    async def stream(
        self,
        messages: List[LLMMessage],
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 8192,
    ) -> AsyncGenerator[str, None]: ...
