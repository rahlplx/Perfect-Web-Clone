"""Typed models for MCP tool inputs and outputs."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ToolName(str, Enum):
    SHELL = "shell"
    WRITE_FILE = "write_file"
    READ_FILE = "read_file"
    EDIT_FILE = "edit_file"
    DELETE_FILE = "delete_file"
    LIST_FILES = "list_files"
    GET_STATE = "get_state"
    TAKE_SCREENSHOT = "take_screenshot"
    RUN_COMMAND = "run_command"
    QUERY_JSON_SOURCE = "query_json_source"


class ShellInput(BaseModel):
    command: str
    timeout: Optional[float] = 30.0
    background: Optional[bool] = False


class WriteFileInput(BaseModel):
    path: str
    content: str


class ReadFileInput(BaseModel):
    path: str
    line_numbers: Optional[bool] = False


class EditFileInput(BaseModel):
    path: str
    old_text: str
    new_text: str


class DeleteFileInput(BaseModel):
    path: str
    recursive: Optional[bool] = False


class ListFilesInput(BaseModel):
    path: Optional[str] = "/"
    recursive: Optional[bool] = False


class RunCommandInput(BaseModel):
    command: str
    args: Optional[List[str]] = None
    timeout: Optional[float] = 60.0
    background: Optional[bool] = False


class TakeScreenshotInput(BaseModel):
    selector: Optional[str] = None
    full_page: Optional[bool] = False
    format: Optional[str] = "png"
    quality: Optional[int] = 80


class QueryJsonSourceInput(BaseModel):
    source_id: Optional[str] = None
    query: Optional[str] = None


class ToolResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None


# Union type for all tool inputs
ToolInput = Union[
    ShellInput,
    WriteFileInput,
    ReadFileInput,
    EditFileInput,
    DeleteFileInput,
    ListFilesInput,
    RunCommandInput,
    TakeScreenshotInput,
    QueryJsonSourceInput,
]


def parse_tool_input(tool_name: ToolName, data: Dict[str, Any]) -> ToolInput:
    """Parse raw dict input into typed model."""
    if tool_name == ToolName.SHELL:
        return ShellInput(**data)
    elif tool_name == ToolName.WRITE_FILE:
        return WriteFileInput(**data)
    elif tool_name == ToolName.READ_FILE:
        return ReadFileInput(**data)
    elif tool_name == ToolName.EDIT_FILE:
        return EditFileInput(**data)
    elif tool_name == ToolName.DELETE_FILE:
        return DeleteFileInput(**data)
    elif tool_name == ToolName.LIST_FILES:
        return ListFilesInput(**data)
    elif tool_name == ToolName.RUN_COMMAND:
        return RunCommandInput(**data)
    elif tool_name == ToolName.TAKE_SCREENSHOT:
        return TakeScreenshotInput(**data)
    elif tool_name == ToolName.QUERY_JSON_SOURCE:
        return QueryJsonSourceInput(**data)
    else:
        raise ValueError(f"Unknown tool: {tool_name}")
