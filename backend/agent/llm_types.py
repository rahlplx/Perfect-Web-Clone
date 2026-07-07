"""Typed models for LLM messages and responses."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ContentBlock(BaseModel):
    type: str = "text"
    text: Optional[str] = None
    tool_use_id: Optional[str] = None
    content: Optional[str] = None


class ToolUseBlock(BaseModel):
    type: str = "tool_use"
    id: str
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)


class ToolResultBlock(BaseModel):
    type: str = "tool_result"
    tool_use_id: str
    content: Union[str, List[ContentBlock]]


class Message(BaseModel):
    role: MessageRole
    content: Union[str, List[Union[ContentBlock, ToolUseBlock, ToolResultBlock]]]


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    stop_reason: Optional[str] = None
    tool_uses: List[ToolUseBlock] = Field(default_factory=list)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    model: str = "claude-3-5-sonnet-20241022"
    max_tokens: int = 8192
    temperature: float = 0.7
    tools: List[ToolDefinition] = Field(default_factory=list)


def messages_from_dicts(raw_messages: List[Dict[str, Any]]) -> List[Message]:
    """Convert raw dicts to typed Message objects."""
    return [Message(**m) for m in raw_messages]


def response_to_dict(response: LLMResponse) -> Dict[str, Any]:
    """Convert typed response to raw dict."""
    return response.model_dump(exclude_none=True)
