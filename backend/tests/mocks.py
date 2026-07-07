"""
Mock objects for testing.
Provides test doubles for WebSocket, LLM, and executor dependencies.
"""

from __future__ import annotations
import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field


class MockWebSocketManager:
    """Mock WebSocket manager for testing MCPToolExecutor."""

    def __init__(self):
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._state: Dict[str, Any] = {}
        self._execute_calls: List[Dict[str, Any]] = []

    def set_response(self, action_type: str, response: Dict[str, Any]):
        """Set expected response for an action type."""
        self._actions[action_type] = response

    def set_state(self, state: Dict[str, Any]):
        """Set the webcontainer state."""
        self._state = state

    async def execute_action(
        self,
        session_id: str,
        action_type: str,
        payload: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Mock execute_action implementation."""
        self._execute_calls.append({
            "session_id": session_id,
            "action_type": action_type,
            "payload": payload,
            "timeout": timeout,
        })
        return self._actions.get(action_type, {"success": True, "result": ""})

    def get_webcontainer_state(self, session_id: str) -> Dict[str, Any]:
        """Mock get_webcontainer_state implementation."""
        return self._state

    def get_execute_calls(self) -> List[Dict[str, Any]]:
        """Get all execute_action calls made."""
        return self._execute_calls

    def clear_calls(self):
        """Clear recorded calls."""
        self._execute_calls.clear()


class MockLLMResponse:
    """Mock LLM response object."""

    def __init__(self, content: str = "Mock response", model: str = "mock-model"):
        self.content = [type("TextBlock", (), {"text": content})()]
        self.model = model
        self.usage = type("Usage", (), {"input_tokens": 10, "output_tokens": 20})()
        self.stop_reason = "end_turn"


class MockAnthropicClient:
    """Mock Anthropic client for testing BaseWorkerAgent."""

    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or ["Mock response"]
        self._call_count = 0
        self._calls: List[Dict[str, Any]] = []

    async def create_message(self, **kwargs) -> MockLLMResponse:
        """Mock create_message implementation."""
        self._calls.append(kwargs)
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return MockLLMResponse(content=response_text)

    def get_calls(self) -> List[Dict[str, Any]]:
        """Get all create_message calls."""
        return self._calls


class MockOpenAIClient:
    """Mock OpenAI client for testing proxy fallback."""

    def __init__(self, responses: Optional[List[str]] = None):
        self._responses = responses or ["Mock OpenAI response"]
        self._call_count = 0
        self._calls: List[Dict[str, Any]] = []

    async def chat_completions_create(self, **kwargs) -> MockLLMResponse:
        """Mock chat.completions.create implementation."""
        self._calls.append(kwargs)
        response_text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return MockLLMResponse(content=response_text, model="gpt-4")

    def get_calls(self) -> List[Dict[str, Any]]:
        """Get all chat.completions.create calls."""
        return self._calls


class ConcreteWorkerAgent:
    """Concrete implementation of BaseWorkerAgent for testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._tools: List[Dict[str, Any]] = []
        self._system_prompt = "Test system prompt"
        self._initial_prompt = "Test initial prompt"
        self._tool_results: Dict[str, Any] = {}
        self._run_calls: List[Dict[str, Any]] = []

    def _get_tools(self) -> List[Dict[str, Any]]:
        return self._tools

    def _build_system_prompt(self) -> str:
        return self._system_prompt

    def _build_initial_prompt(self, retry_attempt: int = 0) -> str:
        return self._initial_prompt

    async def _execute_tool(self, name: str, input_data: Dict[str, Any]) -> Any:
        return self._tool_results.get(name, "ok")

    def _make_result(self, success: bool, **kwargs) -> Dict[str, Any]:
        return {"success": success, **kwargs}

    def set_tool_result(self, tool_name: str, result: Any):
        """Set mock result for a tool."""
        self._tool_results[tool_name] = result


class ConcreteMCPExecutor:
    """Concrete implementation of BaseMCPExecutor for testing."""

    def __init__(self):
        self._unknown_tool_result = ("Unknown tool", True)

    def _handle_unknown_tool(self, tool_name: str, input_data: Dict[str, Any]):
        return self._unknown_tool_result

    def set_unknown_tool_result(self, result):
        """Set the result for unknown tools."""
        self._unknown_tool_result = result


class MockMemoryStore:
    """Mock memory store for testing cache operations."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._get_calls: List[str] = []
        self._set_calls: List[tuple] = []
        self._delete_calls: List[str] = []

    async def get(self, key: str) -> Optional[Any]:
        self._get_calls.append(key)
        return self._store.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        self._set_calls.append((key, value, ttl))
        self._store[key] = value
        return True

    async def delete(self, key: str) -> bool:
        self._delete_calls.append(key)
        return self._store.pop(key, None) is not None

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def get_get_calls(self) -> List[str]:
        return self._get_calls

    def get_set_calls(self) -> List[tuple]:
        return self._set_calls

    def get_delete_calls(self) -> List[str]:
        return self._delete_calls
