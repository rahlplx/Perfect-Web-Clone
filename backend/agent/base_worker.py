"""
Base Worker Agent

Shared logic for WebContainer and BoxLite worker agents.
Template Method pattern: subclass overrides hooks, base owns flow.
"""

from __future__ import annotations
import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

import anthropic
from openai import AsyncOpenAI, APIError as OpenAIAPIError

logger = logging.getLogger(__name__)

# ============================================
# Shared Types
# ============================================

OnToolCallCallback = Callable[[str, str, str, Dict[str, Any]], Awaitable[None]]
OnToolResultCallback = Callable[[str, str, str, str, bool], Awaitable[None]]
OnIterationCallback = Callable[[str, str, int, int], Awaitable[None]]
OnTextDeltaCallback = Callable[[str, str, str, int], Awaitable[None]]
OnFileWrittenCallback = Callable[[str, str, str], Awaitable[None]]


class WorkerErrorType:
    NONE = "none"
    NO_FILES = "no_files"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation"
    TIMEOUT = "timeout"
    EMPTY_HTML = "empty_html"
    UNKNOWN = "unknown"


# ============================================
# Shared Config
# ============================================

@dataclass
class BaseWorkerConfig:
    """Shared worker config fields"""
    worker_id: str
    section_name: str
    task_description: str
    context_data: Dict[str, Any] = field(default_factory=dict)
    target_files: List[str] = field(default_factory=list)
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192
    max_iterations: int = 50
    framework: str = "react"
    styling: str = "tailwind"
    display_name: str = ""


@dataclass
class BaseWorkerResult:
    """Shared worker result fields"""
    worker_id: str
    section_name: str
    success: bool
    error: Optional[str] = None
    error_type: str = WorkerErrorType.NONE
    files: Dict[str, str] = field(default_factory=dict)
    summary: str = ""
    iterations: int = 0
    duration_ms: int = 0
    retry_count: int = 0


# ============================================
# Claude Client Singleton
# ============================================

_anthropic_client: Optional[anthropic.AsyncAnthropic] = None
_openai_client: Optional[AsyncOpenAI] = None


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic()
    return _anthropic_client


def _get_openai_client() -> Optional[AsyncOpenAI]:
    global _openai_client
    if os.getenv("USE_CLAUDE_PROXY", "").lower() in ("true", "1", "yes"):
        if _openai_client is None:
            _openai_client = AsyncOpenAI(
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url=os.getenv("OPENAI_BASE_URL", ""),
            )
        return _openai_client
    return None


# ============================================
# Base Worker (Template Method)
# ============================================

class BaseWorkerAgent(ABC):
    """
    Template Method pattern for worker agents.

    Subclass must implement:
    - _get_tools() -> list of tool definitions
    - _build_system_prompt() -> system prompt string
    - _build_initial_prompt(retry_attempt) -> user prompt string
    - _execute_tool(name, input) -> tool result string
    - _make_result(success, error, error_type, files, ...) -> Result dataclass
    - _reset_state_hook() -> extra reset logic (optional)
    """

    def __init__(
        self,
        config: BaseWorkerConfig,
        on_tool_call: Optional[OnToolCallCallback] = None,
        on_tool_result: Optional[OnToolResultCallback] = None,
        on_iteration: Optional[OnIterationCallback] = None,
        on_text_delta: Optional[OnTextDeltaCallback] = None,
    ):
        self.config = config
        self.worker_id = config.worker_id
        self.section_name = config.section_name

        # Callbacks
        self.on_tool_call = on_tool_call
        self.on_tool_result = on_tool_result
        self.on_iteration = on_iteration
        self.on_text_delta = on_text_delta

        # State
        self.files: Dict[str, str] = {}
        self.is_complete = False
        self.completion_summary = ""
        self.iteration_count = 0

        # LLM client
        self._client = _get_anthropic_client()
        self._openai_client = _get_openai_client()

    # --- Abstract hooks ---

    @abstractmethod
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Return tool definitions for Claude API"""
        ...

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """Build the system prompt"""
        ...

    @abstractmethod
    def _build_initial_prompt(self, retry_attempt: int = 0) -> str:
        """Build the initial user prompt"""
        ...

    @abstractmethod
    async def _execute_tool(self, name: str, input_data: Dict[str, Any]) -> str:
        """Execute a tool call and return result string"""
        ...

    @abstractmethod
    def _make_result(
        self,
        success: bool,
        error: Optional[str] = None,
        error_type: str = WorkerErrorType.NONE,
        files: Optional[Dict[str, str]] = None,
        summary: str = "",
        iterations: int = 0,
        duration_ms: int = 0,
        retry_count: int = 0,
    ) -> BaseWorkerResult:
        """Create result dataclass (subclass returns its own type)"""
        ...

    def _reset_state_hook(self):
        """Optional extra reset logic for subclass"""
        pass

    async def _call_api(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ):
        """
        Call LLM API. Override in subclass for custom client setup.

        Default uses self._client (Anthropic) with self._openai_client fallback.
        """
        if self._openai_client:
            return await self._call_via_proxy(system_prompt, messages, tools)
        return await self._client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            system=system_prompt,
            messages=messages,
            tools=tools if tools else anthropic.NOT_GIVEN,
        )

    # --- Shared implementation ---

    def _reset_state(self):
        self.files = {}
        self.is_complete = False
        self.completion_summary = ""
        self.iteration_count = 0
        self._reset_state_hook()

    async def run(self, max_retries: int = 3) -> BaseWorkerResult:
        """
        Run worker with retry loop. Template Method.
        """
        start_time = datetime.now()
        retry_count = 0
        last_error = None
        last_error_type = WorkerErrorType.UNKNOWN

        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"Worker {self.worker_id}: Retry {retry_count}/{max_retries}")
                    self._reset_state()

                system_prompt = self._build_system_prompt()
                messages = [{
                    "role": "user",
                    "content": self._build_initial_prompt(retry_attempt=retry_count),
                }]

                await self._agent_loop(system_prompt, messages)

                if len(self.files) == 0:
                    last_error = "Worker completed but generated 0 files"
                    last_error_type = WorkerErrorType.NO_FILES
                    logger.warning(f"Worker {self.worker_id}: {last_error} (attempt {retry_count + 1})")
                    retry_count += 1
                    continue

                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                return self._make_result(
                    success=True,
                    error_type=WorkerErrorType.NONE,
                    files=self.files,
                    summary=self.completion_summary or f"Generated {len(self.files)} files",
                    iterations=self.iteration_count,
                    duration_ms=duration_ms,
                    retry_count=retry_count,
                )

            except anthropic.APIError as e:
                last_error = f"API Error: {str(e)}"
                last_error_type = WorkerErrorType.API_ERROR
                logger.error(f"Worker {self.worker_id} API error: {e}")
                retry_count += 1

            except OpenAIAPIError as e:
                last_error = f"Proxy API Error: {str(e)}"
                last_error_type = WorkerErrorType.API_ERROR
                logger.error(f"Worker {self.worker_id} proxy API error: {e}")
                retry_count += 1

            except Exception as e:
                last_error = str(e)
                last_error_type = WorkerErrorType.UNKNOWN
                logger.error(f"Worker {self.worker_id} error: {e}", exc_info=True)
                retry_count += 1

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        logger.error(f"Worker {self.worker_id}: All {max_retries} retries exhausted. Last: {last_error}")

        return self._make_result(
            success=False,
            error=last_error,
            error_type=last_error_type,
            files=self.files,
            summary=f"Failed after {retry_count} attempts: {last_error}",
            iterations=self.iteration_count,
            duration_ms=duration_ms,
            retry_count=retry_count,
        )

    async def _agent_loop(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
    ):
        """Shared agent loop with Claude API"""
        tools = self._get_tools()

        while self.iteration_count < self.config.max_iterations and not self.is_complete:
            self.iteration_count += 1
            logger.debug(f"Worker {self.worker_id} iteration {self.iteration_count}")

            if self.on_iteration:
                try:
                    await self.on_iteration(
                        self.worker_id, self.section_name,
                        self.iteration_count, self.config.max_iterations,
                    )
                except Exception as e:
                    logger.warning(f"Iteration callback error: {e}")

            try:
                response = await self._call_api(system_prompt, messages, tools)

                assistant_content = []
                has_tool_use = False

                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})

                        if self.on_text_delta:
                            try:
                                await self.on_text_delta(
                                    self.worker_id, self.section_name,
                                    block.text, self.iteration_count,
                                )
                            except Exception as e:
                                logger.warning(f"Text delta callback error: {e}")

                    elif block.type == "tool_use":
                        has_tool_use = True

                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                        if self.on_tool_call:
                            try:
                                await self.on_tool_call(
                                    self.worker_id, self.section_name,
                                    block.name, block.input,
                                )
                            except Exception as e:
                                logger.warning(f"Tool call callback error: {e}")

                        tool_result = await self._execute_tool(block.name, block.input)

                        if self.on_tool_result:
                            try:
                                result_preview = tool_result[:500] + "..." if len(tool_result) > 500 else tool_result
                                await self.on_tool_result(
                                    self.worker_id, self.section_name,
                                    block.name, result_preview, True,
                                )
                            except Exception as e:
                                logger.warning(f"Tool result callback error: {e}")

                        messages.append({"role": "assistant", "content": assistant_content})
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result,
                            }],
                        })
                        assistant_content = []

                if not has_tool_use:
                    self.is_complete = True

            except Exception as e:
                logger.error(f"Worker {self.worker_id} loop error: {e}", exc_info=True)
                raise

    async def _call_via_proxy(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
    ):
        """Call Claude via OpenAI-compatible proxy"""
        import re as _re

        def _convert_tools(tools):
            converted = []
            for tool in tools:
                converted.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {}),
                    },
                })
            return converted

        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            if msg["role"] == "assistant":
                text_parts = [b["text"] for b in msg["content"] if b.get("type") == "text"]
                tool_calls = []
                for b in msg["content"]:
                    if b.get("type") == "tool_use":
                        tool_calls.append({
                            "id": b["id"],
                            "type": "function",
                            "function": {
                                "name": b["name"],
                                "arguments": json.dumps(b["input"]),
                            },
                        })
                openai_msg = {"role": "assistant", "content": "\n".join(text_parts) if text_parts else None}
                if tool_calls:
                    openai_msg["tool_calls"] = tool_calls
                openai_messages.append(openai_msg)
            elif msg["role"] == "user":
                if isinstance(msg["content"], list):
                    for block in msg["content"]:
                        if block.get("type") == "tool_result":
                            openai_messages.append({
                                "role": "tool",
                                "tool_call_id": block["tool_use_id"],
                                "content": block.get("content", ""),
                            })
                else:
                    openai_messages.append(msg)

        response = await self._openai_client.chat.completions.create(
            model=self.config.model,
            messages=openai_messages,
            tools=_convert_tools(tools) if tools else None,
            max_tokens=self.config.max_tokens,
        )

        choice = response.choices[0]
        content = []

        if choice.message.content:
            content.append({"type": "text", "text": choice.message.content})

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args,
                })

        class _Resp:
            pass

        resp = _Resp()
        resp.content = [type("Block", (), {"type": c["type"], **c})() for c in content]
        return resp
