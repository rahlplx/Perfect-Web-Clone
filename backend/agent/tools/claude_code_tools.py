"""
Claude Code Style Tools

实现Claude Code风格的工具包装器(Glob, Grep, Bash等)。

工具命名规范:
- Glob (FJ1) - 文件模式匹配搜索
- Grep (XJ1) - 内容正则搜索
- Bash - 系统命令执行
- LS - 目录列表

这些工具是对现有WebContainer工具的封装,提供Claude Code兼容的接口。
"""

from __future__ import annotations
import re
import fnmatch
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .webcontainer_tools import (
    ToolResult,
    list_files,
    get_project_structure,
    search_in_file,
    search_in_project,
    run_command,
)


# ============================================
# Glob Tool (FJ1 - File Pattern Matching)
# ============================================

def glob(
    pattern: str,
    path: str = "/",
    max_results: int = 100,
    webcontainer_state: Optional[dict] = None
) -> ToolResult:
    """
    Glob - Fast file pattern matching (类似Claude Code的FJ1工具)

    使用glob模式搜索文件:
    - "**/*.js" - 所有JS文件
    - "src/**/*.tsx" - src下所有TSX文件
    - "*.json" - 根目录下JSON文件

    Args:
        pattern: Glob模式 (如 "**/*.js", "src/**/*.tsx")
        path: 搜索起始路径 (默认 "/")
        max_results: 最大结果数 (默认 100)
        webcontainer_state: WebContainer状态

    Returns:
        ToolResult with matching file paths
    """
    if not webcontainer_state:
        return ToolResult(
            success=False,
            result="WebContainer state not available"
        )

    files = webcontainer_state.get("files", {})

    if not files:
        return ToolResult(
            success=True,
            result="Project is empty. No files to search."
        )

    # Normalize path
    base_path = path.rstrip("/")
    if base_path and not base_path.startswith("/"):
        base_path = "/" + base_path

    # Match files against pattern
    matched_files = []

    for file_path in files.keys():
        # Normalize file path
        normalized = file_path if file_path.startswith("/") else "/" + file_path

        # Skip node_modules by default
        if "node_modules" in normalized:
            continue

        # Check if under base path
        if base_path and not normalized.startswith(base_path):
            continue

        # Get relative path from base
        if base_path:
            relative = normalized[len(base_path):].lstrip("/")
        else:
            relative = normalized.lstrip("/")

        # Match against glob pattern
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(normalized, pattern):
            matched_files.append(normalized)

            if len(matched_files) >= max_results:
                break

    if not matched_files:
        return ToolResult(
            success=True,
            result=f"No files matching pattern '{pattern}' in {path}"
        )

    # Sort by modification time (newest first) - simulate
    # In real implementation, would use file stats
    matched_files.sort()

    # Format output
    lines = [f"Files matching '{pattern}' (found {len(matched_files)}):"]
    lines.append("-" * 60)

    for file_path in matched_files:
        # Get file size info if available
        content = files.get(file_path, "")
        size = len(content)
        lines.append(f"  📄 {file_path} ({size:,} bytes)")

    if len(matched_files) >= max_results:
        lines.append(f"\n⚠️  Results limited to {max_results}. Use more specific pattern to narrow search.")

    return ToolResult(
        success=True,
        result="\n".join(lines)
    )


# ============================================
# Grep Tool (XJ1 - Content Search)
# ============================================

def grep(
    pattern: str,
    path: Optional[str] = None,
    file_pattern: str = "*",
    ignore_case: bool = True,
    max_results: int = 50,
    context_lines: int = 0,
    webcontainer_state: Optional[dict] = None
) -> ToolResult:
    """
    Grep - Content search with regex (类似Claude Code的XJ1工具)

    在文件中搜索匹配的内容:
    - 支持正则表达式
    - 可选择忽略大小写
    - 可显示上下文行
    - 可按文件模式过滤

    Args:
        pattern: 正则表达式模式
        path: 指定文件路径(可选,不指定则搜索整个项目)
        file_pattern: 文件过滤模式 (如 "*.js", "src/**/*.tsx")
        ignore_case: 是否忽略大小写 (默认 True)
        max_results: 最大结果数 (默认 50)
        context_lines: 上下文行数 (默认 0)
        webcontainer_state: WebContainer状态

    Returns:
        ToolResult with matching lines
    """
    if not webcontainer_state:
        return ToolResult(
            success=False,
            result="WebContainer state not available"
        )

    # If path specified, search in single file
    if path:
        return search_in_file(
            path=path,
            pattern=pattern,
            webcontainer_state=webcontainer_state
        )

    # Otherwise search across project
    return search_in_project(
        pattern=pattern,
        file_pattern=file_pattern,
        webcontainer_state=webcontainer_state
    )


# ============================================
# LS Tool (Directory Listing)
# ============================================

def ls(
    path: str = "/",
    show_hidden: bool = False,
    recursive: bool = False,
    webcontainer_state: Optional[dict] = None
) -> ToolResult:
    """
    LS - List directory contents (类似Unix ls命令)

    列出指定路径的文件和目录。

    Args:
        path: 目录路径 (默认 "/")
        show_hidden: 显示隐藏文件 (默认 False)
        recursive: 递归显示子目录 (默认 False)
        webcontainer_state: WebContainer状态

    Returns:
        ToolResult with directory listing
    """
    if not webcontainer_state:
        return ToolResult(
            success=False,
            result="WebContainer state not available"
        )

    if recursive:
        # For recursive listing, use project structure
        return get_project_structure(webcontainer_state)
    else:
        # For single directory, use list_files
        return list_files(path, webcontainer_state)


# ============================================
# Bash Tool (Command Execution)
# ============================================

def bash(
    command: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    timeout: int = 30000,
    webcontainer_state: Optional[dict] = None
) -> ToolResult:
    """
    Bash - Execute shell command (类似Claude Code的Bash工具)

    在WebContainer终端中执行命令。

    支持的命令:
    - npm, node, npx
    - ls, cat, pwd, echo
    - git (基础命令)
    - 其他Node.js环境支持的命令

    Args:
        command: 命令名称 (如 "npm", "node", "ls")
        args: 命令参数列表 (可选)
        cwd: 工作目录 (可选)
        timeout: 超时时间(毫秒) (默认 30000)
        webcontainer_state: WebContainer状态

    Returns:
        ToolResult with command output (includes action for frontend)
    """
    if not webcontainer_state:
        return ToolResult(
            success=False,
            result="WebContainer state not available"
        )

    # Parse command if args not provided
    if args is None:
        parts = command.split()
        command = parts[0]
        args = parts[1:] if len(parts) > 1 else []

    # Security check - block potentially dangerous commands
    dangerous_commands = ["rm -rf /", "dd if=", "mkfs", ":(){ :|:& };:"]
    full_cmd = f"{command} {' '.join(args)}"

    for dangerous in dangerous_commands:
        if dangerous in full_cmd:
            return ToolResult(
                success=False,
                result=f"Command blocked for security: {full_cmd}"
            )

    # Use run_command from webcontainer_tools
    return run_command(command=command, args=args)


# ============================================
# Tool Definitions for Claude API
# ============================================

def get_claude_code_tool_definitions() -> List[dict]:
    """
    获取Claude Code风格工具的定义

    Returns:
        List of tool definitions in Claude API format
    """
    return [
        {
            "name": "glob",
            "description": """Search for files using glob patterns. Fast file pattern matching similar to find command.

Examples:
- glob(pattern="**/*.js") - Find all JavaScript files
- glob(pattern="src/**/*.tsx") - Find all TSX files in src
- glob(pattern="*.json", path="/") - Find JSON files in root

Supports wildcards:
- * matches any characters in a filename
- ** matches any number of directories
- ? matches single character""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g., '**/*.js', 'src/**/*.tsx')"
                    },
                    "path": {
                        "type": "string",
                        "description": "Starting directory path (default '/')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default 100)"
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "grep",
            "description": """Search for content using regex patterns. Powerful content search across files.

Examples:
- grep(pattern="function\\s+\\w+") - Find function definitions
- grep(pattern="TODO|FIXME", ignore_case=true) - Find todos
- grep(pattern="import.*Component", file_pattern="*.{jsx,tsx,vue,svelte}") - Find component imports

Features:
- Regex support with full syntax
- Case-insensitive search option
- File pattern filtering
- Shows matching lines with line numbers""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "path": {
                        "type": "string",
                        "description": "Specific file to search (optional, searches all if not specified)"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Filter files by pattern (e.g., '*.js', 'src/**/*.tsx'). Default '*'"
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "Ignore case in search (default true)"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results to return (default 50)"
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines to show (default 0)"
                    }
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "ls",
            "description": """List directory contents. Similar to Unix ls command.

Examples:
- ls() - List root directory
- ls(path="/src") - List src directory
- ls(path="/", recursive=true) - Show full project tree
- ls(show_hidden=true) - Include hidden files

Shows:
- Files with 📄 icon
- Directories with 📁 icon
- File/directory names""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default '/')"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Show hidden files starting with . (default false)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Show full tree recursively (default false)"
                    }
                },
                "required": []
            }
        },
        {
            "name": "bash",
            "description": """Execute shell commands in WebContainer terminal.

IMPORTANT: This runs in a Node.js WebContainer environment, NOT a full Linux shell.

Supported commands:
- npm, node, npx - Node.js package management
- ls, cat, pwd, echo - Basic shell commands
- git - Basic git operations
- Common Unix utilities available in Node.js

Examples:
- bash(command="npm install")
- bash(command="node -v")
- bash(command="ls -la")
- bash(command="pwd")

NOT supported:
- System package managers (apt, yum, brew)
- Low-level system commands (dd, mkfs)
- Commands requiring root access

The command output will be captured and returned.""",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute (can include arguments, or use args parameter)"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command arguments as array (optional if included in command)"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (optional)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in milliseconds (default 30000, max 600000)"
                    }
                },
                "required": ["command"]
            }
        }
    ]


# ============================================
# Tool Registry
# ============================================

CLAUDE_CODE_TOOLS = {
    "glob": glob,
    "grep": grep,
    "ls": ls,
    "bash": bash,
}


def get_claude_code_tools():
    """Get all Claude Code-style tools"""
    return CLAUDE_CODE_TOOLS
