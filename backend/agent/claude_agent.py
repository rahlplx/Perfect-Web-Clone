"""
Claude Agent SDK Integration

Main entry point for Claude Agent SDK with WebContainer MCP tools.

Features:
- Claude API integration
- Tool execution via MCP
- Memory management (three-tier)
- Streaming responses
"""

from __future__ import annotations
import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import anthropic
from openai import AsyncOpenAI, APIError as OpenAIAPIError

from .websocket_manager import WebSocketManager, get_ws_manager
from .mcp_server import WebContainerMCPServer, create_mcp_server
from .memory_sdk import SDKMemoryManager, create_memory_manager
from .prompts import get_system_prompt
from cache.memory_store import extraction_cache

logger = logging.getLogger(__name__)


# ============================================
# Configuration
# ============================================

@dataclass
class AgentConfig:
    """Agent configuration"""
    # Main Agent uses Sonnet 3.5 for orchestration
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192  # Sonnet 3.5 supports up to 8192
    max_iterations: int = 999999  # Unlimited
    temperature: float = 0.7
    enable_tools: bool = True


# Model max_tokens limits
MODEL_MAX_TOKENS = {
    # Haiku 4.5 - supports higher output
    "claude-haiku-4-5-20251001": 16384,
    # Haiku 3.5 - max 8192
    "claude-3-5-haiku-20241022": 8192,
    "claude-3-5-haiku-latest": 8192,
    # Sonnet 4.5 - supports 16384 output
    "claude-sonnet-4-5-20250929": 16384,
    # Sonnet 4 models
    "claude-sonnet-4-20250514": 16384,
    "claude-3-5-sonnet-20241022": 8192,
    "claude-3-5-sonnet-latest": 8192,
    # Default fallback
    "default": 8192,
}


def _get_max_tokens_for_model(model: str) -> int:
    """Get max_tokens limit for a specific model"""
    return MODEL_MAX_TOKENS.get(model, MODEL_MAX_TOKENS["default"])


def _is_proxy_enabled() -> bool:
    """Check if Claude proxy is enabled"""
    return os.getenv("USE_CLAUDE_PROXY", "").lower() in ("true", "1", "yes")


# ============================================
# Agent Session
# ============================================

@dataclass
class AgentSession:
    """
    Agent session state

    Holds all state for a single agent conversation.
    """
    session_id: str
    user_id: Optional[str] = None

    # Components
    memory: SDKMemoryManager = field(default_factory=lambda: create_memory_manager())
    mcp_server: Optional[WebContainerMCPServer] = None

    # State
    iteration_count: int = 0
    is_running: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    # Configuration
    config: AgentConfig = field(default_factory=AgentConfig)

    # 新增：多轮对话追踪
    conversation_round: int = 0  # 当前对话轮次
    last_file_operations: list = field(default_factory=list)  # 最近的文件操作记录


# ============================================
# Claude Agent
# ============================================

class ClaudeAgent:
    """
    Claude Agent with WebContainer MCP tools

    Main agent class that orchestrates:
    - Message handling
    - Tool execution
    - Memory management
    - Streaming responses
    """

    def __init__(
        self,
        ws_manager: WebSocketManager,
        session_id: str,
        user_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
    ):
        """
        Initialize Claude Agent

        Args:
            ws_manager: WebSocket manager for frontend communication
            session_id: Session ID
            user_id: Optional user ID
            config: Agent configuration
        """
        self.ws_manager = ws_manager
        self.session_id = session_id
        self.config = config or AgentConfig()

        # Check if using proxy
        self.use_proxy = _is_proxy_enabled()

        if self.use_proxy:
            # Use Claude proxy (supports both Anthropic and OpenAI formats)
            proxy_api_key = os.getenv("CLAUDE_PROXY_API_KEY")
            proxy_base_url = os.getenv("CLAUDE_PROXY_BASE_URL", "")
            proxy_model = os.getenv("CLAUDE_PROXY_MODEL")

            if not proxy_api_key:
                raise ValueError("CLAUDE_PROXY_API_KEY environment variable not set")

            # Check if using Anthropic native format (URL contains /messages)
            if "/messages" in proxy_base_url.lower():
                # Anthropic native format - extract base URL without /v1/messages
                # e.g., https://yinli.one/v1/messages -> https://yinli.one
                # Handle both /v1/messages and /V1/messages (case-insensitive)
                import re
                base_url = re.sub(r'/v1/messages', '', proxy_base_url, flags=re.IGNORECASE)
                base_url = re.sub(r'/messages', '', base_url, flags=re.IGNORECASE)
                self.anthropic_client = anthropic.AsyncAnthropic(
                    api_key=proxy_api_key,
                    base_url=base_url,
                    timeout=120.0,
                )
                self.openai_client = None
                logger.info(f"Using Anthropic-native proxy: {base_url}")
            else:
                # OpenAI-compatible format
                self.openai_client = AsyncOpenAI(
                    api_key=proxy_api_key,
                    base_url=proxy_base_url,
                    timeout=120.0,
                )
                self.anthropic_client = None
                logger.info(f"Using OpenAI-compatible proxy: {proxy_base_url}")

            # Override model if proxy model is configured
            # Priority: CLAUDE_PROXY_MODEL_MAIN > CLAUDE_PROXY_MODEL > default
            proxy_model_main = os.getenv("CLAUDE_PROXY_MODEL_MAIN")
            effective_model = proxy_model_main or proxy_model

            if effective_model:
                self.config.model = effective_model
                # Auto-adjust max_tokens based on model limits
                model_max = _get_max_tokens_for_model(effective_model)
                if self.config.max_tokens > model_max:
                    logger.info(f"[MainAgent] Adjusting max_tokens from {self.config.max_tokens} to {model_max} for model {effective_model}")
                    self.config.max_tokens = model_max
                logger.info(f"[MainAgent] Using model: {effective_model} (max_tokens={self.config.max_tokens})")
        else:
            # Use direct Anthropic API
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set")

            self.anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
            self.openai_client = None
            logger.info("Using direct Anthropic API")

        # Initialize components
        self.memory = create_memory_manager()
        self.mcp_server = create_mcp_server(ws_manager, session_id)

        # Session state
        self.session = AgentSession(
            session_id=session_id,
            user_id=user_id,
            memory=self.memory,
            mcp_server=self.mcp_server,
            config=self.config,
        )

        logger.info(f"ClaudeAgent initialized: session={session_id}")

    # ============================================
    # Message Processing
    # ============================================

    async def process_message(
        self,
        message: str,
        webcontainer_state: Optional[Dict[str, Any]] = None,
        selected_source_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process user message and generate response

        Main entry point for handling user input.

        Args:
            message: User message
            webcontainer_state: Current WebContainer state
            selected_source_id: Selected JSON source ID for reference data

        Yields:
            Response events (text, tool_call, tool_result, done, error)
        """
        if self.session.is_running:
            yield {"type": "error", "error": "Agent is already processing"}
            return

        self.session.is_running = True
        self.session.iteration_count = 0

        # 新增：递增对话轮次
        self.session.conversation_round += 1
        current_round = self.session.conversation_round
        logger.info(f"[Agent] Starting conversation round {current_round}")

        try:
            # Update WebContainer state if provided in message
            if webcontainer_state:
                self.ws_manager.update_webcontainer_state(
                    self.session_id,
                    webcontainer_state,
                )
                logger.info(
                    f"[Agent] Round {current_round}: Updated state from message, "
                    f"files={len(webcontainer_state.get('files', {}))}"
                )

            # 关键修复：多轮对话时总是请求刷新状态
            # 因为消息中的状态可能是用户点击发送时的快照，不是最新的
            if current_round > 1:
                logger.info(f"[Agent] Round {current_round}: Refreshing state for multi-round sync...")
                await self.ws_manager.request_state_refresh(self.session_id)
            elif not webcontainer_state:
                # 第一轮如果没有状态也要请求
                logger.info(f"[Agent] Round {current_round}: No state in message, requesting refresh...")
                await self.ws_manager.request_state_refresh(self.session_id)

            # Add user message to memory
            self.memory.add_user_message(message)

            # Build system prompt
            base_prompt = get_system_prompt()

            # Add selected source context if available
            logger.info(f"[Process Message] selected_source_id = {selected_source_id}")
            if selected_source_id:
                logger.info(f"[Process Message] Fetching source context for: {selected_source_id}")
                source_context = await self._fetch_source_context(selected_source_id)
                if source_context:
                    base_prompt = f"{base_prompt}\n\n{source_context}"
                    logger.info(f"[Process Message] ✅ Added source context ({len(source_context)} chars)")
                else:
                    logger.warning(f"[Process Message] ❌ Failed to get source context for: {selected_source_id}")
            else:
                logger.info("[Process Message] No selected_source_id provided")

            system_prompt = self.memory.build_system_prompt(base_prompt)

            # Get conversation history
            messages = self.memory.get_messages_for_api()

            # Run agent loop
            async for event in self._agent_loop(system_prompt, messages):
                yield event

        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            yield {"type": "error", "error": str(e)}

        finally:
            self.session.is_running = False
            yield {"type": "done"}

    # ============================================
    # Agent Loop
    # ============================================

    async def _agent_loop(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Main agent loop

        Continues until:
        - No more tool calls
        - Max iterations reached
        - Error occurs

        Args:
            system_prompt: System prompt
            messages: Conversation messages

        Yields:
            Response events
        """
        tools = self.mcp_server.get_tools_for_claude_api()

        while self.session.iteration_count < self.config.max_iterations:
            self.session.iteration_count += 1

            logger.info(f"Agent iteration {self.session.iteration_count}")

            # Yield iteration event
            yield {
                "type": "iteration",
                "iteration": self.session.iteration_count,
            }

            try:
                # Call Claude API
                response = await self._call_claude(
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools if self.config.enable_tools else None,
                )

                # Process response
                assistant_content = []
                has_tool_use = False

                for block in response.content:
                    if block.type == "text":
                        # Yield text
                        yield {"type": "text", "content": block.text}
                        assistant_content.append({
                            "type": "text",
                            "text": block.text,
                        })

                    elif block.type == "tool_use":
                        has_tool_use = True

                        # Yield tool call
                        yield {
                            "type": "tool_call",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }

                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })

                        # Execute tool
                        logger.info(f"Executing tool: {block.name}")
                        tool_result = await self.mcp_server.handle_tool_use(
                            tool_use_id=block.id,
                            tool_name=block.name,
                            tool_input=block.input,
                        )

                        # Yield tool result
                        yield {
                            "type": "tool_result",
                            "id": block.id,
                            "success": not tool_result.get("is_error", False),
                            "result": tool_result.get("content", ""),
                        }

                        # Add to messages for next iteration
                        messages.append({
                            "role": "assistant",
                            "content": assistant_content,
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": tool_result.get("content", ""),
                                "is_error": tool_result.get("is_error", False),
                            }],
                        })

                        # Reset for next tool
                        assistant_content = []

                # Add final assistant message to memory
                if assistant_content:
                    text_content = " ".join(
                        b.get("text", "") for b in assistant_content
                        if b.get("type") == "text"
                    )
                    if text_content:
                        self.memory.add_assistant_message(text_content)

                # Check if should continue
                if not has_tool_use:
                    logger.info("No tool calls, agent complete")
                    break

                if response.stop_reason == "end_turn":
                    logger.info("End turn, agent complete")
                    break

            except (anthropic.APIError, OpenAIAPIError) as e:
                logger.error(f"API error: {e}")
                yield {"type": "error", "error": f"API error: {str(e)}"}
                break

            except Exception as e:
                logger.error(f"Unexpected error in agent loop: {e}", exc_info=True)
                yield {"type": "error", "error": str(e)}
                break

    # ============================================
    # Claude API Call
    # ============================================

    async def _call_claude(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Call Claude API (supports both direct Anthropic and OpenAI-compatible proxy)

        Args:
            system_prompt: System prompt
            messages: Conversation messages
            tools: Tool definitions

        Returns:
            API response (unified format)
        """
        # Use Anthropic client if available (either direct or native proxy)
        if self.anthropic_client:
            return await self._call_anthropic_direct(system_prompt, messages, tools)
        else:
            # Use OpenAI-compatible proxy
            return await self._call_openai_proxy(system_prompt, messages, tools)

    async def _call_anthropic_direct(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> anthropic.types.Message:
        """Call direct Anthropic API"""
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        return await self.anthropic_client.messages.create(**kwargs)

    async def _call_openai_proxy(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Call OpenAI-compatible proxy API

        Converts Anthropic format to OpenAI format and response back.
        """
        # Convert messages to OpenAI format
        openai_messages = [{"role": "system", "content": system_prompt}]

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if isinstance(content, str):
                openai_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Handle structured content (tool_use, tool_result, etc.)
                combined_content = self._convert_content_to_openai(content, role)
                if combined_content:
                    openai_messages.append(combined_content)

        # Convert tools to OpenAI format
        openai_tools = None
        if tools:
            openai_tools = self._convert_tools_to_openai(tools)

        # Call OpenAI API
        kwargs = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": openai_messages,
        }

        if openai_tools:
            kwargs["tools"] = openai_tools

        response = await self.openai_client.chat.completions.create(**kwargs)

        # Convert response to Anthropic format
        return self._convert_openai_response_to_anthropic(response)

    def _convert_content_to_openai(
        self,
        content: List[Dict[str, Any]],
        role: str,
    ) -> Optional[Dict[str, Any]]:
        """Convert Anthropic content blocks to OpenAI message format"""
        if role == "assistant":
            # Handle assistant message with potential tool calls
            text_parts = []
            tool_calls = []

            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input", {})),
                        }
                    })

            result = {"role": "assistant", "content": " ".join(text_parts) if text_parts else None}
            if tool_calls:
                result["tool_calls"] = tool_calls
            return result

        elif role == "user":
            # Handle user message with potential tool results
            for block in content:
                if block.get("type") == "tool_result":
                    return {
                        "role": "tool",
                        "tool_call_id": block.get("tool_use_id"),
                        "content": block.get("content", ""),
                    }

            # Regular user content
            text_parts = []
            for block in content:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return {"role": "user", "content": " ".join(text_parts)}

        return None

    def _convert_tools_to_openai(
        self,
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Convert Anthropic tools to OpenAI format"""
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {}),
                }
            })
        return openai_tools

    def _convert_openai_response_to_anthropic(self, response):
        """Convert OpenAI response to Anthropic-like format"""
        choice = response.choices[0] if response.choices else None
        if not choice:
            raise ValueError("No response from OpenAI API")

        message = choice.message

        # Build content blocks in Anthropic format
        content = []

        # Add text content
        if message.content:
            content.append(_MockBlock("text", text=message.content))

        # Add tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                try:
                    input_data = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    input_data = {}

                content.append(_MockBlock(
                    "tool_use",
                    id=tool_call.id,
                    name=tool_call.function.name,
                    input=input_data,
                ))

        # Create mock response object
        return _MockAnthropicResponse(
            content=content,
            stop_reason=choice.finish_reason,
        )


    # ============================================
    # Source Context
    # ============================================

    async def _fetch_source_context(self, source_id: str) -> Optional[str]:
        """
        Fetch JSON source data and format it for system prompt

        Args:
            source_id: JSON source ID from memory cache

        Returns:
            Formatted source context string, or None if not found
        """
        try:
            # Fetch from memory cache (open-source version)
            logger.info(f"[Source Context] Fetching source: {source_id}")
            entry = extraction_cache.get(source_id)

            if not entry:
                logger.warning(f"[Source Context] Source NOT FOUND in cache: {source_id}")
                # List available cache entries for debugging
                all_entries = extraction_cache.list_all()
                logger.info(f"[Source Context] Available entries: {[e.id for e in all_entries]}")
                return None

            # Extract data from cache entry
            source_url = entry.url
            page_title = entry.title
            raw_json = entry.data

            logger.info(f"[Source Context] Found source: {page_title} ({source_url})")
            logger.info(f"[Source Context] Data keys: {list(raw_json.keys()) if raw_json else 'None'}")

            # Format source context - IMPORTANT: Tell the agent it HAS a source selected
            context_parts = [
                "",
                "=" * 60,
                "## 🎯 SELECTED SOURCE WEBSITE DATA (Ready for Cloning)",
                "=" * 60,
                "",
                f"**Source URL:** {source_url or 'Unknown'}",
                f"**Page Title:** {page_title or 'Unknown'}",
                f"**Source ID:** `{source_id}`",
                "",
                "⚠️ IMPORTANT: The user has ALREADY selected this website to clone.",
                "You should IMMEDIATELY proceed with cloning using `get_layout()` tool.",
                "DO NOT ask for a URL - you already have all the data you need!",
                "",
                "### Available Data Structure:",
            ]

            # Add top-level keys summary
            if isinstance(raw_json, dict):
                for key, value in list(raw_json.items())[:15]:  # Limit to 15 keys
                    if isinstance(value, dict):
                        context_parts.append(f"- **{key}**: object ({len(value)} properties)")
                    elif isinstance(value, list):
                        context_parts.append(f"- **{key}**: array ({len(value)} items)")
                    elif isinstance(value, str):
                        preview = value[:100] + "..." if len(value) > 100 else value
                        context_parts.append(f"- **{key}**: \"{preview}\"")
                    else:
                        context_parts.append(f"- **{key}**: {type(value).__name__}")

                if len(raw_json) > 15:
                    context_parts.append(f"- ... and {len(raw_json) - 15} more properties")

            context_parts.append("")
            context_parts.append("### Next Steps:")
            context_parts.append(f"1. Call `get_layout(source_id=\"{source_id}\")` to analyze the page structure")
            context_parts.append("2. Call `spawn_section_workers()` to generate the components")
            context_parts.append("3. Write App.jsx and index.css to integrate everything")
            context_parts.append("")
            context_parts.append("=" * 60)

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"[Source Context] Failed to fetch source context: {e}", exc_info=True)
            return None

    # ============================================
    # Utility Methods
    # ============================================

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "session_id": self.session_id,
            "iteration_count": self.session.iteration_count,
            "is_running": self.session.is_running,
            "memory_stats": self.memory.get_stats(),
            "created_at": self.session.created_at.isoformat(),
        }


# ============================================
# Mock Classes for OpenAI Compatibility
# ============================================

class _MockBlock:
    """Mock Anthropic content block for OpenAI compatibility"""

    def __init__(self, block_type: str, **kwargs):
        self.type = block_type
        for key, value in kwargs.items():
            setattr(self, key, value)


class _MockAnthropicResponse:
    """Mock Anthropic response for OpenAI compatibility"""

    def __init__(self, content: List, stop_reason: str):
        self.content = content
        self.stop_reason = stop_reason


# ============================================
# Factory Functions
# ============================================

def create_agent(
    session_id: str,
    user_id: Optional[str] = None,
    config: Optional[AgentConfig] = None,
) -> ClaudeAgent:
    """
    Create a new Claude Agent

    Args:
        session_id: Session ID
        user_id: Optional user ID
        config: Agent configuration

    Returns:
        Configured Claude Agent
    """
    ws_manager = get_ws_manager()
    return ClaudeAgent(
        ws_manager=ws_manager,
        session_id=session_id,
        user_id=user_id,
        config=config,
    )


# ============================================
# Agent Registry
# ============================================

# Active agents: session_id -> ClaudeAgent
_agents: Dict[str, ClaudeAgent] = {}


def get_agent(session_id: str) -> Optional[ClaudeAgent]:
    """Get agent by session ID"""
    return _agents.get(session_id)


def register_agent(agent: ClaudeAgent):
    """Register an agent"""
    _agents[agent.session_id] = agent
    logger.info(f"Agent registered: {agent.session_id}")


def unregister_agent(session_id: str):
    """Unregister an agent"""
    if session_id in _agents:
        del _agents[session_id]
        logger.info(f"Agent unregistered: {session_id}")


def get_or_create_agent(
    session_id: str,
    user_id: Optional[str] = None,
    config: Optional[AgentConfig] = None,
) -> ClaudeAgent:
    """Get existing agent or create new one"""
    agent = get_agent(session_id)
    if not agent:
        agent = create_agent(session_id, user_id, config)
        register_agent(agent)
    return agent
