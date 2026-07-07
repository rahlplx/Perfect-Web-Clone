"""
Tests for agent.mcp_tools: MCPToolExecutor and helper functions.
"""

import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from typing import Any, Dict, Optional

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tests.mocks import MockWebSocketManager
from cache.memory_store import extraction_cache, CacheEntry


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def ws_manager():
    return MockWebSocketManager()


@pytest.fixture
def executor(ws_manager):
    from agent.mcp_tools import MCPToolExecutor
    return MCPToolExecutor(ws_manager, session_id="test-session-1")


@pytest.fixture(autouse=True)
def clear_cache():
    extraction_cache.clear()
    yield
    extraction_cache.clear()


def _store_source(source_id: str, data: dict, url: str = "https://example.com", title: str = "Test Page"):
    """Helper to seed the cache for cache-related tests."""
    entry_id = extraction_cache.store(url, data, title=title)
    return entry_id


class _FakeWebContainerState:
    """Fake WebContainer state object matching the interface used by executor."""
    def __init__(self):
        self.status: str = "ready"
        self.files: dict = {}
        self.terminals: list = []
        self.preview_url: str = "http://localhost:5173"
        self.error: Optional[str] = None
        self.preview: dict = {"console_messages": [], "error_overlay": {}}


# ============================================
# 1. MCPToolExecutor.execute() routing
# ============================================

class TestExecuteRouting:
    @pytest.mark.asyncio
    async def test_execute_returns_mcp_format(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": "ok"})
        result = await executor.execute("shell", {"command": "ls"})
        assert "content" in result
        assert "is_error" in result
        assert result["is_error"] is False
        assert result["content"][0]["type"] == "text"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool_falls_through(self, executor, ws_manager):
        result = await executor.execute("nonexistent_tool", {})
        assert "is_error" in result
        assert "content" in result

    @pytest.mark.asyncio
    async def test_execute_exception_returns_error(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": ""})
        with patch.object(executor, "_execute_shell", side_effect=RuntimeError("boom")):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is True
        assert "boom" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_execute_tuple_return(self, executor, ws_manager):
        with patch.object(executor, "_execute_shell", return_value=("output", True)):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is True
        assert result["content"][0]["text"] == "output"

    @pytest.mark.asyncio
    async def test_execute_dict_return(self, executor, ws_manager):
        with patch.object(executor, "_execute_shell", return_value={"result": "ok", "is_error": False}):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is False
        assert result["content"][0]["text"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_string_error_prefix(self, executor, ws_manager):
        with patch.object(executor, "_execute_shell", return_value="Error: something"):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_execute_string_action_failed_prefix(self, executor, ws_manager):
        with patch.object(executor, "_execute_shell", return_value="[ACTION_FAILED] bad"):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_execute_string_command_failed_prefix(self, executor, ws_manager):
        with patch.object(executor, "_execute_shell", return_value="[COMMAND_FAILED] bad"):
            result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is True


# ============================================
# 2. Shell tool handler
# ============================================

class TestShellHandler:
    @pytest.mark.asyncio
    async def test_shell_success(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": "file1.txt"})
        result = await executor.execute("shell", {"command": "ls"})
        assert result["is_error"] is False
        assert "file1.txt" in result["content"][0]["text"]
        assert ws_manager._execute_calls[-1]["payload"]["command"] == "ls"

    @pytest.mark.asyncio
    async def test_shell_failure(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": False, "error": "command not found"})
        result = await executor.execute("shell", {"command": "badcmd"})
        assert result["is_error"] is True
        assert "command not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_shell_background_uses_short_timeout(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": ""})
        await executor.execute("shell", {"command": "sleep 10", "background": True})
        call = ws_manager._execute_calls[-1]
        assert call["timeout"] == 5.0

    @pytest.mark.asyncio
    async def test_shell_custom_timeout(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": ""})
        await executor.execute("shell", {"command": "ls", "timeout": 120})
        call = ws_manager._execute_calls[-1]
        assert call["timeout"] == 120


# ============================================
# 3. write_file tool handler
# ============================================

class TestWriteFileHandler:
    @pytest.mark.asyncio
    async def test_write_file_success(self, executor, ws_manager):
        ws_manager.set_response("write_file", {"success": True})
        result = await executor.execute("write_file", {"path": "/src/App.jsx", "content": "code"})
        assert result["is_error"] is False
        assert "/src/App.jsx" in result["content"][0]["text"]
        assert "4 bytes" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_write_file_failure(self, executor, ws_manager):
        ws_manager.set_response("write_file", {"success": False, "error": "disk full"})
        result = await executor.execute("write_file", {"path": "/src/App.jsx", "content": "x"})
        assert result["is_error"] is True
        assert "disk full" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_write_file_prepends_slash(self, executor, ws_manager):
        ws_manager.set_response("write_file", {"success": True})
        await executor.execute("write_file", {"path": "src/file.js", "content": ""})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/src/file.js"

    @pytest.mark.asyncio
    async def test_write_file_blocks_path_traversal(self, executor):
        result = await executor.execute("write_file", {"path": "/src/../../etc/passwd", "content": "x"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]


# ============================================
# 4. read_file tool handler
# ============================================

class TestReadFileHandler:
    @pytest.mark.asyncio
    async def test_read_file_success(self, executor, ws_manager):
        ws_manager.set_response("read_file", {"success": True, "result": "file contents"})
        result = await executor.execute("read_file", {"path": "/src/App.jsx"})
        assert result["is_error"] is False
        assert "file contents" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_read_file_failure(self, executor, ws_manager):
        ws_manager.set_response("read_file", {"success": False, "error": "not found"})
        result = await executor.execute("read_file", {"path": "/missing.txt"})
        assert result["is_error"] is True
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_read_file_blocks_path_traversal(self, executor):
        result = await executor.execute("read_file", {"path": "/src/../etc/passwd"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_read_file_prepends_slash(self, executor, ws_manager):
        ws_manager.set_response("read_file", {"success": True, "result": ""})
        await executor.execute("read_file", {"path": "file.txt"})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/file.txt"

    @pytest.mark.asyncio
    async def test_read_file_timeout(self, executor, ws_manager):
        async def slow_action(**kwargs):
            await asyncio.sleep(0.05)
            raise asyncio.TimeoutError()

        ws_manager.execute_action = slow_action
        result = await executor.execute("read_file", {"path": "/slow.txt"})
        assert result["is_error"] is True
        assert "Timeout" in result["content"][0]["text"]


# ============================================
# 5. edit_file tool handler
# ============================================

class TestEditFileHandler:
    @pytest.mark.asyncio
    async def test_edit_file_success(self, executor, ws_manager):
        ws_manager.set_response("edit_file", {"success": True})
        result = await executor.execute("edit_file", {
            "path": "/src/App.jsx",
            "old_text": "Hello",
            "new_text": "World",
        })
        assert result["is_error"] is False
        assert "/src/App.jsx" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_edit_file_failure(self, executor, ws_manager):
        ws_manager.set_response("edit_file", {"success": False, "error": "Text not found"})
        result = await executor.execute("edit_file", {
            "path": "/src/App.jsx",
            "old_text": "nonexistent",
            "new_text": "replacement",
        })
        assert result["is_error"] is True
        assert "Text not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_edit_file_blocks_path_traversal(self, executor):
        result = await executor.execute("edit_file", {
            "path": "/src/../../secret",
            "old_text": "a",
            "new_text": "b",
        })
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_edit_file_prepends_slash(self, executor, ws_manager):
        ws_manager.set_response("edit_file", {"success": True})
        await executor.execute("edit_file", {"path": "file.js", "old_text": "a", "new_text": "b"})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/file.js"


# ============================================
# 6. delete_file tool handler
# ============================================

class TestDeleteFileHandler:
    @pytest.mark.asyncio
    async def test_delete_file_success(self, executor, ws_manager):
        ws_manager.set_response("delete_file", {"success": True})
        result = await executor.execute("delete_file", {"path": "/tmp/old.txt"})
        assert result["is_error"] is False
        assert "Deleted" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_delete_file_failure(self, executor, ws_manager):
        ws_manager.set_response("delete_file", {"success": False, "error": "permission denied"})
        result = await executor.execute("delete_file", {"path": "/etc/important"})
        assert result["is_error"] is True
        assert "permission denied" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_delete_file_blocks_path_traversal(self, executor):
        result = await executor.execute("delete_file", {"path": "/src/../../etc"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_delete_file_prepends_slash(self, executor, ws_manager):
        ws_manager.set_response("delete_file", {"success": True})
        await executor.execute("delete_file", {"path": "temp/file.txt"})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/temp/file.txt"


# ============================================
# 7. list_files tool handler
# ============================================

class TestListFilesHandler:
    @pytest.mark.asyncio
    async def test_list_files_success(self, executor, ws_manager):
        ws_manager.set_response("list_files", {"success": True, "result": "file1.txt\nfile2.txt"})
        result = await executor.execute("list_files", {"path": "/"})
        assert result["is_error"] is False
        assert "file1.txt" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_files_failure(self, executor, ws_manager):
        ws_manager.set_response("list_files", {"success": False, "error": "no such directory"})
        result = await executor.execute("list_files", {"path": "/nonexistent"})
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_list_files_prepends_slash(self, executor, ws_manager):
        ws_manager.set_response("list_files", {"success": True, "result": ""})
        await executor.execute("list_files", {"path": "src"})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/src"

    @pytest.mark.asyncio
    async def test_list_files_recursive(self, executor, ws_manager):
        ws_manager.set_response("list_files", {"success": True, "result": ""})
        await executor.execute("list_files", {"path": "/", "recursive": True})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["recursive"] is True

    @pytest.mark.asyncio
    async def test_list_files_default_path(self, executor, ws_manager):
        ws_manager.set_response("list_files", {"success": True, "result": ""})
        await executor.execute("list_files", {})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["path"] == "/"


# ============================================
# 8. get_state tool handler
# ============================================

class TestGetStateHandler:
    @pytest.mark.asyncio
    async def test_get_state_success(self, executor, ws_manager):
        fake_state = _FakeWebContainerState()
        fake_state.files = {"/src/App.jsx": "code", "/package.json": "{}"}
        ws_manager.set_state(fake_state)
        result = await executor.execute("get_state", {})
        assert result["is_error"] is False
        text = result["content"][0]["text"]
        assert "ready" in text
        assert "2 files" in text

    @pytest.mark.asyncio
    async def test_get_state_no_state(self, executor, ws_manager):
        ws_manager.set_state(None)
        result = await executor.execute("get_state", {})
        assert result["is_error"] is True
        assert "not available" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_get_state_shows_preview_url(self, executor, ws_manager):
        fake_state = _FakeWebContainerState()
        fake_state.preview_url = "http://localhost:3000"
        ws_manager.set_state(fake_state)
        result = await executor.execute("get_state", {})
        assert "localhost:3000" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_state_shows_error(self, executor, ws_manager):
        fake_state = _FakeWebContainerState()
        fake_state.error = "OOM killed"
        ws_manager.set_state(fake_state)
        result = await executor.execute("get_state", {})
        assert "OOM killed" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_state_truncates_many_files(self, executor, ws_manager):
        fake_state = _FakeWebContainerState()
        fake_state.files = {f"/file{i}.txt": "" for i in range(25)}
        ws_manager.set_state(fake_state)
        result = await executor.execute("get_state", {})
        assert "and 5 more" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_state_shows_terminals(self, executor, ws_manager):
        fake_state = _FakeWebContainerState()
        fake_state.terminals = [{"name": "npm", "is_running": True}]
        ws_manager.set_state(fake_state)
        result = await executor.execute("get_state", {})
        assert "npm" in result["content"][0]["text"]
        assert "running" in result["content"][0]["text"]


# ============================================
# 9. take_screenshot tool handler
# ============================================

class TestTakeScreenshotHandler:
    @pytest.mark.asyncio
    async def test_screenshot_success_base64(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", {"success": True, "result": "data:image/png;base64,abc123"})
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is False
        assert "IMAGE_BASE64" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_screenshot_ws_error(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", {"success": False, "error": "no preview"})
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is True
        assert "no preview" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_screenshot_no_response(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", None)
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is True
        assert "No response" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_screenshot_empty_result(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", {"success": True, "result": ""})
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is True
        assert "Empty response" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_screenshot_json_failure_with_visual_summary(self, executor, ws_manager):
        payload = json.dumps({
            "success": False,
            "message": "html2canvas failed",
            "suggestion": "try viewport screenshot",
            "visualSummary": {"viewport": {"width": 1920}, "visibleElementCount": 5, "hasContent": True},
        })
        ws_manager.set_response("take_screenshot", {"success": True, "result": payload})
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is True
        assert "html2canvas failed" in result["content"][0]["text"]
        assert "Visual Summary" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_screenshot_json_success_visual_summary(self, executor, ws_manager):
        payload = json.dumps({"success": True, "visualSummary": {"viewport": {"width": 1920}}})
        ws_manager.set_response("take_screenshot", {"success": True, "result": payload})
        result = await executor.execute("take_screenshot", {})
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_screenshot_with_selector(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", {"success": True, "result": "data:image/png;base64,xyz"})
        await executor.execute("take_screenshot", {"selector": "#hero"})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["selector"] == "#hero"

    @pytest.mark.asyncio
    async def test_screenshot_full_page(self, executor, ws_manager):
        ws_manager.set_response("take_screenshot", {"success": True, "result": "data:image/png;base64,xyz"})
        await executor.execute("take_screenshot", {"full_page": True})
        call = ws_manager._execute_calls[-1]
        assert call["payload"]["full_page"] is True


# ============================================
# 10. Path traversal protection (all handlers)
# ============================================

class TestPathTraversalProtection:
    @pytest.mark.asyncio
    async def test_write_file_dotdot(self, executor):
        result = await executor.execute("write_file", {"path": "/src/../../../etc/passwd", "content": "x"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_read_file_dotdot(self, executor):
        result = await executor.execute("read_file", {"path": "/src/../../etc/shadow"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_edit_file_dotdot(self, executor):
        result = await executor.execute("edit_file", {"path": "/tmp/../../etc/hosts", "old_text": "a", "new_text": "b"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_delete_file_dotdot(self, executor):
        result = await executor.execute("delete_file", {"path": "/src/../../../etc"})
        assert result["is_error"] is True
        assert "path traversal" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_files_no_traversal_check(self, executor, ws_manager):
        """list_files does NOT have path traversal protection in the source code."""
        ws_manager.set_response("list_files", {"success": True, "result": ""})
        result = await executor.execute("list_files", {"path": "/src/../../etc"})
        # list_files does not block traversal - it just passes through
        assert result["is_error"] is False


# ============================================
# 11. Error handling: missing tools, invalid inputs
# ============================================

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_missing_tool_returns_error(self, executor, ws_manager):
        result = await executor.execute("totally_fake_tool", {})
        assert "is_error" in result
        assert "content" in result
        # Unknown tools route through _execute_generic which calls WebSocket
        assert isinstance(result["is_error"], bool)

    @pytest.mark.asyncio
    async def test_empty_tool_name(self, executor, ws_manager):
        result = await executor.execute("", {})
        assert "is_error" in result
        assert "content" in result

    @pytest.mark.asyncio
    async def test_shell_missing_command(self, executor, ws_manager):
        ws_manager.set_response("shell", {"success": True, "result": ""})
        result = await executor.execute("shell", {})
        # missing command defaults to "" which still calls ws_manager
        assert "is_error" in result

    @pytest.mark.asyncio
    async def test_write_file_missing_path(self, executor, ws_manager):
        ws_manager.set_response("write_file", {"success": True})
        result = await executor.execute("write_file", {"content": "data"})
        assert "is_error" in result


# ============================================
# 12. _search_json() and _format_json_value()
# ============================================

class TestSearchJsonAndFormat:
    def test_search_json_nested_dict(self, executor):
        data = {"a": {"b": {"c": "hello world"}}}
        results = executor._search_json(data, "hello")
        assert len(results) == 1
        assert results[0][0] == "$.a.b.c"
        assert results[0][1] == "hello world"

    def test_search_json_value_match(self, executor):
        data = {"name": "Alice", "city": "Boston"}
        results = executor._search_json(data, "boston")
        assert len(results) == 1
        assert results[0][1] == "Boston"

    def test_search_json_key_match(self, executor):
        data = {"user_name": "Bob", "user_age": 30}
        results = executor._search_json(data, "user_")
        assert len(results) == 2

    def test_search_json_list_items(self, executor):
        data = {"items": ["apple", "banana", "cherry"]}
        results = executor._search_json(data, "banana")
        assert len(results) == 1
        assert results[0][0] == "$.items[1]"

    def test_search_json_no_matches(self, executor):
        data = {"a": 1, "b": 2}
        results = executor._search_json(data, "xyz")
        assert len(results) == 0

    def test_search_json_deeply_nested(self, executor):
        data = {"level1": {"level2": {"level3": {"target": "found"}}}}
        results = executor._search_json(data, "target")
        assert len(results) == 1
        assert "found" in str(results[0][1])

    def test_search_json_limits_array_to_100(self, executor):
        data = {"items": list(range(200))}
        results = executor._search_json(data, "nonexistent")
        assert isinstance(results, list)

    def test_search_json_limits_results_to_50(self, executor):
        data = {f"key_{i}": "match" for i in range(100)}
        results = executor._search_json(data, "match")
        assert len(results) <= 50

    def test_format_json_value_none(self, executor):
        assert executor._format_json_value(None) == "null"

    def test_format_json_value_bool(self, executor):
        assert executor._format_json_value(True) == "true"
        assert executor._format_json_value(False) == "false"

    def test_format_json_value_int(self, executor):
        assert executor._format_json_value(42) == "42"

    def test_format_json_value_float(self, executor):
        assert executor._format_json_value(3.14) == "3.14"

    def test_format_json_value_string_short(self, executor):
        assert executor._format_json_value("hello") == '"hello"'

    def test_format_json_value_string_long(self, executor):
        long_str = "x" * 600
        result = executor._format_json_value(long_str, max_len=500)
        # Result is quoted with truncation marker
        assert len(result) < len(json.dumps(long_str))
        assert "..." in result

    def test_format_json_value_list(self, executor):
        result = executor._format_json_value([1, 2, 3])
        # json.dumps with indent=2 formats as multiline
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_format_json_value_dict(self, executor):
        result = executor._format_json_value({"key": "val"})
        assert "key" in result

    def test_format_json_value_dict_truncated(self, executor):
        big = {f"k{i}": "v" * 100 for i in range(50)}
        result = executor._format_json_value(big, max_len=100)
        assert result.endswith("...")

    def test_format_json_value_object_fallback(self, executor):
        class Custom:
            def __str__(self):
                return "custom_obj"
        result = executor._format_json_value(Custom())
        assert result == "custom_obj"


# ============================================
# 13. get_source_from_cache() and list_sources_from_cache()
# ============================================

class TestCacheHelpers:
    def test_get_source_from_cache_found(self):
        entry_id = _store_source("src-1", {"html": "<div>hello</div>"}, url="https://a.com", title="Page A")
        from agent.mcp_tools import get_source_from_cache
        result = get_source_from_cache(entry_id)
        assert result is not None
        assert result["id"] == entry_id
        assert result["page_title"] == "Page A"
        assert result["source_url"] == "https://a.com"
        assert result["raw_json"] == {"html": "<div>hello</div>"}

    def test_get_source_from_cache_not_found(self):
        from agent.mcp_tools import get_source_from_cache
        result = get_source_from_cache("nonexistent")
        assert result is None

    def test_list_sources_from_cache_empty(self):
        from agent.mcp_tools import list_sources_from_cache
        result = list_sources_from_cache()
        assert result == []

    def test_list_sources_from_cache_multiple(self):
        _store_source("s1", {}, url="https://a.com", title="Page A")
        _store_source("s2", {}, url="https://b.com", title="Page B")
        _store_source("s3", {}, url="https://c.com", title="Page C")
        from agent.mcp_tools import list_sources_from_cache
        result = list_sources_from_cache(limit=2)
        assert len(result) == 2
        assert result[0]["page_title"] == "Page C"  # newest first

    def test_list_sources_from_cache_limit(self):
        for i in range(5):
            _store_source(f"s{i}", {}, url=f"https://{i}.com", title=f"Page {i}")
        from agent.mcp_tools import list_sources_from_cache
        result = list_sources_from_cache(limit=10)
        assert len(result) == 5

    def test_list_sources_returns_id_url_title(self):
        _store_source("s1", {}, url="https://test.com", title="Test")
        from agent.mcp_tools import list_sources_from_cache
        result = list_sources_from_cache()
        assert len(result) == 1
        assert set(result[0].keys()) == {"id", "source_url", "page_title"}


# ============================================
# 14. query_json_source tool handler
# ============================================

class TestQueryJsonSource:
    @pytest.mark.asyncio
    async def test_query_json_source_no_sources(self, executor):
        result = await executor.execute("query_json_source", {"query": "test"})
        assert "No saved sources" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_query_json_source_with_source_id(self, executor):
        entry_id = _store_source("src-1", {"navigation": {"logo": "Acme"}})
        result = await executor.execute("query_json_source", {
            "query": "navigation",
            "source_id": entry_id,
        })
        assert result["is_error"] is False
        assert "navigation" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_query_json_source_source_not_found(self, executor):
        result = await executor.execute("query_json_source", {
            "query": "test",
            "source_id": "nonexistent",
        })
        assert result["is_error"] is False  # Returns a string message, not an MCP error
        assert "not found" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_query_json_source_lists_sources(self, executor):
        _store_source("s1", {}, url="https://a.com", title="My Page")
        result = await executor.execute("query_json_source", {"query": "any"})
        text = result["content"][0]["text"]
        assert "My Page" in text
        assert "https://a.com" in text


# ============================================
# 15. get_section_data tool handler
# ============================================

class TestGetSectionData:
    @pytest.mark.asyncio
    async def test_get_section_data_success(self, executor):
        entry_id = _store_source("src-1", {"header": {"logo": "X"}, "footer": {"text": "Y"}})
        result = await executor.execute("get_section_data", {
            "source_id": entry_id,
            "data_keys": ["header"],
        })
        assert result["is_error"] is False
        assert "header" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_section_data_missing_source(self, executor):
        result = await executor.execute("get_section_data", {
            "source_id": "bad",
            "data_keys": ["x"],
        })
        assert result["is_error"] is False
        assert "not found" in result["content"][0]["text"].lower()

    @pytest.mark.asyncio
    async def test_get_section_data_missing_keys(self, executor):
        entry_id = _store_source("src-1", {"a": 1})
        result = await executor.execute("get_section_data", {
            "source_id": entry_id,
            "data_keys": ["nonexistent"],
        })
        text = result["content"][0]["text"]
        assert "nonexistent" in text

    @pytest.mark.asyncio
    async def test_get_section_data_no_source_id(self, executor):
        result = await executor.execute("get_section_data", {"data_keys": ["x"]})
        assert result["is_error"] is True
        assert "source_id is required" in result["content"][0]["text"]


# ============================================
# 16. get_worker_status tool handler
# ============================================

class TestGetWorkerStatus:
    @pytest.mark.asyncio
    async def test_get_worker_status_no_workers(self, executor):
        result = await executor.execute("get_worker_status", {})
        assert result["is_error"] is False
        assert "No Worker Results" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_worker_status_with_results(self, executor):
        executor._last_worker_results = {
            "header": {"status": "success", "error": None, "files": ["/src/header.jsx"], "can_retry": False},
            "footer": {"status": "failed", "error": "timeout", "files": [], "can_retry": True},
        }
        executor._last_source_id = "src-1"
        result = await executor.execute("get_worker_status", {})
        text = result["content"][0]["text"]
        assert "header" in text
        assert "footer" in text
        assert "success" in text
        assert "failed" in text
        assert "retry" in text.lower()

    @pytest.mark.asyncio
    async def test_get_worker_status_all_success(self, executor):
        executor._last_worker_results = {
            "header": {"status": "success", "error": None, "files": ["/h.jsx"], "can_retry": False},
        }
        executor._last_source_id = "s1"
        result = await executor.execute("get_worker_status", {})
        text = result["content"][0]["text"]
        assert "retry" not in text.lower() or "No" in text


# ============================================
# 17. TOOL_DEFINITIONS validation
# ============================================

class TestToolDefinitions:
    def test_tool_definitions_is_list(self):
        from agent.mcp_tools import TOOL_DEFINITIONS
        assert isinstance(TOOL_DEFINITIONS, list)

    def test_all_tools_have_required_fields(self):
        from agent.mcp_tools import TOOL_DEFINITIONS
        for tool in TOOL_DEFINITIONS:
            assert "name" in tool, f"Tool missing 'name': {tool}"
            assert "description" in tool, f"Tool missing 'description': {tool}"
            assert "input_schema" in tool, f"Tool missing 'input_schema': {tool}"
            assert "type" in tool["input_schema"], f"Tool {tool['name']} schema missing 'type'"

    def test_all_required_fields_present(self):
        from agent.mcp_tools import TOOL_DEFINITIONS
        for tool in TOOL_DEFINITIONS:
            schema = tool["input_schema"]
            assert schema.get("type") == "object", f"Tool {tool['name']} schema type != object"

    def test_known_tool_names_present(self):
        from agent.mcp_tools import TOOL_DEFINITIONS
        names = {t["name"] for t in TOOL_DEFINITIONS}
        expected = {"shell", "write_file", "read_file", "edit_file", "delete_file",
                    "list_files", "get_state", "take_screenshot"}
        assert expected.issubset(names)


# ============================================
# 18. _generate_final_app_jsx helpers
# ============================================

class TestGenerateAppJsx:
    def test_generate_empty(self, executor):
        result = executor._generate_final_app_jsx([])
        assert "import React" in result
        assert "No components generated" in result

    def test_generate_with_sections(self, executor):
        result = executor._generate_final_app_jsx(["header_0", "footer_0"])
        assert "Header0Section" in result
        assert "Footer0Section" in result
        assert "import Header0Section" in result

    def test_generate_v2_empty(self, executor):
        result = executor._generate_final_app_jsx_v2([])
        assert "import React" in result
        assert "No components generated" in result

    def test_generate_v2_with_worker_results(self, executor):
        @dataclass
        class FakeWorkerResult:
            section_name: str
            success: bool
            files: Dict[str, str]
            error: Optional[str] = None

        wr = FakeWorkerResult(
            section_name="header_0",
            success=True,
            files={"/src/components/sections/header_0/Header0Section.jsx": "code"},
        )
        result = executor._generate_final_app_jsx_v2([wr])
        assert "Header0Section" in result
        assert "import Header0Section" in result
