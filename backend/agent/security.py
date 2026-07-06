"""
Security utilities for path validation and command sanitization.

All file operations MUST use validate_path() before executing.
All shell commands MUST use sanitize_command() or check_command_allowed().
"""

from __future__ import annotations
import os
import re
from pathlib import Path, PurePosixPath
from typing import Optional


# ============================================
# Path Traversal Protection
# ============================================

class PathTraversalError(Exception):
    """Raised when path escapes sandbox root"""
    pass


def validate_path(path: str, sandbox_root: str) -> str:
    """
    Validate and resolve a path, ensuring it stays within sandbox_root.

    Args:
        path: User-provided path (may contain ../)
        sandbox_root: Absolute path to sandbox directory

    Returns:
        Normalized absolute path within sandbox

    Raises:
        PathTraversalError: If path escapes sandbox
    """
    root = Path(sandbox_root).resolve()

    # Normalize: strip leading slash, resolve .. components
    if path.startswith("/"):
        path = path[1:]

    # Resolve against sandbox root
    resolved = (root / path).resolve()

    # Verify containment
    if not str(resolved).startswith(str(root)):
        raise PathTraversalError(
            f"Path traversal blocked: '{path}' escapes sandbox root '{sandbox_root}'"
        )

    return str(resolved)


def safe_relative_path(path: str, sandbox_root: str) -> str:
    """
    Get a safe relative path string for use in sandbox operations.

    Returns:
        Forward-slash relative path from sandbox root

    Raises:
        PathTraversalError: If path escapes sandbox
    """
    root = Path(sandbox_root).resolve()

    if path.startswith("/"):
        path = path[1:]

    resolved = (root / path).resolve()

    if not str(resolved).startswith(str(root)):
        raise PathTraversalError(
            f"Path traversal blocked: '{path}' escapes sandbox root"
        )

    return resolved.relative_to(root).as_posix()


def normalize_sandbox_path(path: str) -> str:
    """
    Normalize a path for consistent sandbox usage.
    Strips leading slash, resolves . and .. components.

    Does NOT check against sandbox root - use validate_path() for that.
    """
    if path.startswith("/"):
        path = path[1:]

    parts = PurePosixPath(path).parts
    resolved = []
    for part in parts:
        if part == "..":
            if resolved:
                resolved.pop()
        elif part and part != ".":
            resolved.append(part)

    return "/".join(resolved) if resolved else ""


# ============================================
# Shell Command Security
# ============================================

# Commands that are NEVER allowed (destructive, exfiltration, privilege escalation)
BLOCKED_COMMANDS = frozenset([
    "rm", "rmdir", "del", "format", "mkfs",
    "curl", "wget", "fetch", "httpie",
    "eval", "exec", "source", "bash", "sh", "zsh", "fish",
    "su", "sudo", "doas", "runas",
    "chmod", "chown", "chgrp",
    "mount", "umount",
    "kill", "killall", "pkill",
    "nc", "ncat", "netcat", "socat",
    "python", "python3", "ruby", "perl", "php",
    "ssh", "scp", "rsync", "sftp",
    "docker", "podman", "kubectl",
])

# Patterns that indicate shell injection
INJECTION_PATTERNS = [
    r"[;&|]",           # Command separators
    r"\$\(",            # Command substitution
    r"`",               # Backtick substitution
    r"\.\./",           # Path traversal in commands
    r">\s*/",           # Redirect to absolute path
    r"<\s*/",           # Read from absolute path
]

# Safe commands (always allowed)
SAFE_COMMANDS = frozenset([
    "ls", "cat", "head", "tail", "wc", "grep", "find", "file",
    "echo", "printf", "date", "pwd", "whoami", "hostname",
    "mkdir", "touch", "cp", "mv",
    "npm", "npx", "node", "yarn", "pnpm",
    "git",
    "tar", "zip", "unzip", "gzip",
    "diff", "sort", "uniq", "tr", "cut", "sed", "awk",
])


def check_command_allowed(command: str) -> tuple[bool, str]:
    """
    Check if a command is allowed by the security policy.

    Returns:
        (allowed, reason) tuple
    """
    command = command.strip()

    if not command:
        return False, "Empty command"

    # Check for injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, command):
            return False, f"Blocked: shell injection pattern '{pattern}' detected"

    # Extract base command (first word)
    parts = command.split()
    if not parts:
        return False, "Empty command"

    base_cmd = parts[0].split("/")[-1]  # Handle /usr/bin/xxx

    # Check blocked commands
    if base_cmd in BLOCKED_COMMANDS:
        return False, f"Blocked: command '{base_cmd}' is not allowed"

    return True, "Allowed"


def sanitize_command(command: str) -> str:
    """
    Sanitize a command by removing dangerous patterns.

    Returns:
        Sanitized command string

    Raises:
        ValueError: If command is fundamentally unsafe
    """
    allowed, reason = check_command_allowed(command)
    if not allowed:
        raise ValueError(reason)

    # Remove shell metacharacters that could enable injection
    # Keep safe characters for file paths, npm commands, etc.
    sanitized = re.sub(r'[;&|`$]', '', command)

    return sanitized.strip()
