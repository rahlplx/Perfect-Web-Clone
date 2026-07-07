"""
Tests for BoxLite REST API Routes.

Uses httpx.AsyncClient with ASGITransport for FastAPI testing.
Mocks sandbox dependencies so no Docker/filesystem is needed.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, Any
from dataclasses import dataclass

from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from boxlite.routes import boxlite_router
from boxlite.mock_sandbox import MockBoxLiteSandboxManager
from boxlite.models import (
    SandboxState,
    SandboxStatus,
    FileEntry,
    CommandResult,
)
from boxlite.boxlite_tools import ToolResult


# ============================================
# App Setup
# ============================================

def create_test_app():
    """Create a minimal FastAPI app with only the boxlite router."""
    app = FastAPI()
    app.include_router(boxlite_router)
    return app


def make_manager(sandbox_id: str = "test-sandbox") -> MockBoxLiteSandboxManager:
    """Create a MockBoxLiteSandboxManager with .state and .get_state_dict."""
    manager = MockBoxLiteSandboxManager(sandbox_id)
    # Expose _state as public .state (real manager has .state in __init__)
    manager.state = manager._state
    # Add get_state_dict (real manager has this; mock doesn't)
    manager.get_state_dict = lambda: manager.get_state().model_dump(mode="json")
    # Add reconnect as async no-op (real manager has this; mock doesn't)
    manager.reconnect = AsyncMock()
    return manager


def mock_state_dict(manager: MockBoxLiteSandboxManager) -> Dict[str, Any]:
    """Return a state dict compatible with what routes expect."""
    state = manager.get_state()
    return state.model_dump(mode="json")


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_get_sandbox_manager():
    """Patch get_sandbox_manager to return a MockBoxLiteSandboxManager."""
    manager = make_manager("test-sandbox")
    with patch("boxlite.routes.get_sandbox_manager", return_value=manager) as m:
        yield m, manager


@pytest.fixture
def mock_cleanup_sandbox():
    """Patch cleanup_sandbox."""
    with patch("boxlite.routes.cleanup_sandbox", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_unregister_agent():
    """Patch unregister_boxlite_agent."""
    with patch("boxlite.routes.unregister_boxlite_agent") as m:
        yield m


@pytest.fixture
def mock_boxlite_tools():
    """Patch boxlite_tools module with controlled tool functions."""
    mock_write = AsyncMock(
        return_value=ToolResult(success=True, result="File written successfully")
    )
    mock_tool_fn = AsyncMock(
        return_value=ToolResult(success=True, result="Tool executed", data={"key": "val"})
    )
    with patch("boxlite.routes.boxlite_tools") as m:
        m.ALL_TOOLS = {"test_tool": mock_tool_fn}
        m.write_file = mock_write
        m.get_boxlite_tool_definitions = MagicMock(return_value=[{"name": "test_tool"}])
        yield m


# ============================================
# Tests: POST /api/boxlite/sandbox (Create)
# ============================================

@pytest.mark.asyncio
async def test_create_sandbox(mock_get_sandbox_manager, mock_unregister_agent):
    """Create a sandbox with default request body."""
    _, manager = mock_get_sandbox_manager

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox")

    assert resp.status_code == 200
    data = resp.json()
    assert "sandbox_id" in data
    assert data["status"] == "running"
    assert data["ws_url"].startswith("/api/boxlite/ws/")


@pytest.mark.asyncio
async def test_create_sandbox_with_custom_id(mock_get_sandbox_manager, mock_unregister_agent):
    """Create a sandbox with a custom sandbox_id."""
    _, manager = mock_get_sandbox_manager
    manager.sandbox_id = "custom-id"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox",
            json={"sandbox_id": "custom-id"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_id"] == "custom-id"


@pytest.mark.asyncio
async def test_create_sandbox_error(mock_get_sandbox_manager, mock_unregister_agent):
    """Create sandbox returns 500 when get_sandbox_manager raises."""
    mock_get_sandbox_manager[0].side_effect = Exception("boom")

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_create_sandbox_empty_body(mock_get_sandbox_manager, mock_unregister_agent):
    """Create sandbox with empty JSON body (optional fields default to None)."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox", json={})

    assert resp.status_code == 200


# ============================================
# Tests: GET /api/boxlite/sandbox/{sandbox_id}
# ============================================

@pytest.mark.asyncio
async def test_get_sandbox_state(mock_get_sandbox_manager):
    """Get sandbox state returns valid state dict."""
    _, manager = mock_get_sandbox_manager

    with patch.object(manager, "get_state_dict", return_value=mock_state_dict(manager)):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/boxlite/sandbox/test-sandbox")

    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_id"] == "test-sandbox"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_get_sandbox_state_error(mock_get_sandbox_manager):
    """Get sandbox state returns 500 on exception."""
    mock_get_sandbox_manager[0].side_effect = Exception("not found")

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/boxlite/sandbox/nonexistent")

    assert resp.status_code == 500


# ============================================
# Tests: DELETE /api/boxlite/sandbox/{sandbox_id}
# ============================================

@pytest.mark.asyncio
async def test_delete_sandbox(mock_cleanup_sandbox):
    """Delete sandbox returns status deleted."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.delete("/api/boxlite/sandbox/test-sandbox")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "deleted"
    assert data["sandbox_id"] == "test-sandbox"
    mock_cleanup_sandbox.assert_awaited_once_with("test-sandbox")


@pytest.mark.asyncio
async def test_delete_sandbox_error(mock_cleanup_sandbox):
    """Delete sandbox returns 500 on cleanup failure."""
    mock_cleanup_sandbox.side_effect = Exception("cleanup failed")

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.delete("/api/boxlite/sandbox/test-sandbox")

    assert resp.status_code == 500


# ============================================
# Tests: POST /api/boxlite/sandbox/{sandbox_id}/tool
# ============================================

@pytest.mark.asyncio
async def test_execute_tool(mock_get_sandbox_manager, mock_boxlite_tools):
    """Execute a known tool returns success."""
    mock_boxlite_tools.ALL_TOOLS["test_tool"] = AsyncMock(
        return_value=ToolResult(success=True, result="ok", data={"out": 1})
    )

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/tool",
            json={"tool_name": "test_tool", "params": {"arg": "val"}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["result"] == "ok"
    assert data["data"] == {"out": 1}


@pytest.mark.asyncio
async def test_execute_tool_unknown(mock_get_sandbox_manager, mock_boxlite_tools):
    """Execute an unknown tool: route catches HTTPException, returns 200 with success=False."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/tool",
            json={"tool_name": "nonexistent_tool", "params": {}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "Unknown tool" in data["error"]


@pytest.mark.asyncio
async def test_execute_tool_failure(mock_get_sandbox_manager, mock_boxlite_tools):
    """Tool that raises returns success=False with error message."""
    mock_boxlite_tools.ALL_TOOLS["fail_tool"] = AsyncMock(
        side_effect=RuntimeError("tool exploded")
    )

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/tool",
            json={"tool_name": "fail_tool", "params": {}},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "tool exploded" in data["error"]


@pytest.mark.asyncio
async def test_execute_tool_missing_tool_name():
    """Tool execution without tool_name returns 422 validation error."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/tool",
            json={"params": {}},
        )

    assert resp.status_code == 422


# ============================================
# Tests: POST /api/boxlite/sandbox/{sandbox_id}/file (write)
# ============================================

@pytest.mark.asyncio
async def test_write_file(mock_get_sandbox_manager, mock_boxlite_tools):
    """Write file calls boxlite_tools.write_file and returns success."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/file",
            json={"path": "/src/App.jsx", "content": "export default () => <div>Hi</div>"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    mock_boxlite_tools.write_file.assert_awaited_once()


@pytest.mark.asyncio
async def test_write_file_error(mock_get_sandbox_manager, mock_boxlite_tools):
    """Write file returns 500 when write_file raises."""
    mock_boxlite_tools.write_file.side_effect = Exception("disk full")

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/file",
            json={"path": "/test.txt", "content": "data"},
        )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_write_file_missing_content():
    """Write file without content returns 422 validation error."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/file",
            json={"path": "/test.txt"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_write_file_multiple(mock_get_sandbox_manager, mock_boxlite_tools):
    """Write multiple files to same sandbox calls write_file each time."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        r1 = await client.post(
            "/api/boxlite/sandbox/test-sandbox/file",
            json={"path": "/a.txt", "content": "aaa"},
        )
        r2 = await client.post(
            "/api/boxlite/sandbox/test-sandbox/file",
            json={"path": "/b.txt", "content": "bbb"},
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert mock_boxlite_tools.write_file.await_count == 2


# ============================================
# Tests: GET /api/boxlite/sandbox/{sandbox_id}/file (read)
# ============================================

@pytest.mark.asyncio
async def test_read_file(mock_get_sandbox_manager):
    """Read file returns content for existing file."""
    _, manager = mock_get_sandbox_manager
    manager._files["/hello.txt"] = "Hello, World!"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/file",
            params={"path": "/hello.txt"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == "/hello.txt"
    assert data["content"] == "Hello, World!"


@pytest.mark.asyncio
async def test_read_file_not_found(mock_get_sandbox_manager):
    """Read nonexistent file returns 404."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/file",
            params={"path": "/missing.txt"},
        )

    assert resp.status_code == 404
    assert "File not found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_read_file_missing_query_param():
    """Read file without path query param returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/boxlite/sandbox/test-sandbox/file")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_read_file_error(mock_get_sandbox_manager):
    """Read file returns 500 when read_file raises."""
    _, manager = mock_get_sandbox_manager
    with patch.object(manager, "read_file", side_effect=Exception("read error")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.get(
                "/api/boxlite/sandbox/test-sandbox/file",
                params={"path": "/test.txt"},
            )

    assert resp.status_code == 500


# ============================================
# Tests: GET /api/boxlite/sandbox/{sandbox_id}/files (list)
# ============================================

@pytest.mark.asyncio
async def test_list_files(mock_get_sandbox_manager):
    """List files returns entries for a given directory."""
    _, manager = mock_get_sandbox_manager
    manager._files["/src/App.jsx"] = "<div/>"
    manager._files["/src/utils.js"] = "export const x = 1"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/files",
            params={"path": "/src"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == "/src"
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) == 2
    names = {e["name"] for e in data["entries"]}
    assert names == {"App.jsx", "utils.js"}


@pytest.mark.asyncio
async def test_list_files_root(mock_get_sandbox_manager):
    """List files at root returns root entries."""
    _, manager = mock_get_sandbox_manager
    manager._files["/index.html"] = "<!DOCTYPE html>"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/boxlite/sandbox/test-sandbox/files")

    assert resp.status_code == 200
    data = resp.json()
    assert data["path"] == "/"
    assert len(data["entries"]) == 1


@pytest.mark.asyncio
async def test_list_files_error(mock_get_sandbox_manager):
    """List files returns 500 when list_files raises."""
    _, manager = mock_get_sandbox_manager
    with patch.object(manager, "list_files", side_effect=Exception("io error")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/boxlite/sandbox/test-sandbox/files")

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_list_files_with_subdirectories(mock_get_sandbox_manager):
    """List files shows directories when paths have nested structure."""
    _, manager = mock_get_sandbox_manager
    manager._files["/src/components/Button.jsx"] = "export default () => {}"
    manager._files["/src/components/Input.jsx"] = "export default () => {}"
    manager._files["/src/App.jsx"] = "import Button from './components/Button'"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/files",
            params={"path": "/src"},
        )

    assert resp.status_code == 200
    data = resp.json()
    names = {e["name"] for e in data["entries"]}
    assert "App.jsx" in names
    assert "components" in names
    comps = [e for e in data["entries"] if e["name"] == "components"][0]
    assert comps["type"] == "directory"


# ============================================
# Tests: POST /api/boxlite/sandbox/{sandbox_id}/command
# ============================================

@pytest.mark.asyncio
async def test_run_command(mock_get_sandbox_manager):
    """Run command returns success with stdout."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={"command": "echo hello", "background": False},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["exit_code"] == 0
    assert "echo hello" in data["stdout"]


@pytest.mark.asyncio
async def test_run_command_background(mock_get_sandbox_manager):
    """Run command with background=True returns success."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={"command": "sleep 100", "background": True},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_run_command_error(mock_get_sandbox_manager):
    """Run command returns 500 when run_command raises."""
    _, manager = mock_get_sandbox_manager
    with patch.object(manager, "run_command", side_effect=Exception("exec error")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/test-sandbox/command",
                json={"command": "false"},
            )

    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_run_command_exit_code_nonzero(mock_get_sandbox_manager):
    """Run command with exit code 42 returns success=False."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={"command": "exit 42"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["exit_code"] == 42


@pytest.mark.asyncio
async def test_run_command_missing_command():
    """Run command without command field returns 422."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_command_with_special_characters(mock_get_sandbox_manager):
    """Run command with special characters in the command string."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={"command": "echo 'hello world & goodbye'"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "hello world & goodbye" in data["stdout"]


# ============================================
# Tests: POST /api/boxlite/sandbox/{sandbox_id}/dev-server/start
# ============================================

@pytest.mark.asyncio
async def test_start_dev_server(mock_get_sandbox_manager):
    """Start dev server returns success and preview_url."""
    _, manager = mock_get_sandbox_manager
    manager._state.preview_url = "http://localhost:8080"

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox/test-sandbox/dev-server/start")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["preview_url"] == "http://localhost:8080"


@pytest.mark.asyncio
async def test_start_dev_server_error(mock_get_sandbox_manager):
    """Start dev server returns 500 on exception."""
    _, manager = mock_get_sandbox_manager
    with patch.object(manager, "start_dev_server", side_effect=Exception("port busy")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/boxlite/sandbox/test-sandbox/dev-server/start")

    assert resp.status_code == 500


# ============================================
# Tests: POST /api/boxlite/sandbox/{sandbox_id}/dev-server/stop
# ============================================

@pytest.mark.asyncio
async def test_stop_dev_server(mock_get_sandbox_manager):
    """Stop dev server returns success=True."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox/test-sandbox/dev-server/stop")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_stop_dev_server_error(mock_get_sandbox_manager):
    """Stop dev server returns 500 on exception."""
    _, manager = mock_get_sandbox_manager
    with patch.object(manager, "stop_dev_server", side_effect=Exception("cannot stop")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/boxlite/sandbox/test-sandbox/dev-server/stop")

    assert resp.status_code == 500


# ============================================
# Tests: GET /api/boxlite/sandbox/{sandbox_id}/terminal/{terminal_id}/output
# ============================================

@pytest.mark.asyncio
async def test_get_terminal_output(mock_get_sandbox_manager):
    """Get terminal output returns terminal_id and output lines."""
    _, manager = mock_get_sandbox_manager
    manager.get_terminal_output = MagicMock(return_value=["line1", "line2"])

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/terminal/term-1/output",
            params={"lines": 100},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["terminal_id"] == "term-1"
    assert data["output"] == ["line1", "line2"]


@pytest.mark.asyncio
async def test_get_terminal_output_error(mock_get_sandbox_manager):
    """Get terminal output returns 500 on exception."""
    _, manager = mock_get_sandbox_manager
    manager.get_terminal_output = MagicMock(side_effect=Exception("no terminal"))

    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get(
            "/api/boxlite/sandbox/test-sandbox/terminal/term-x/output",
        )

    assert resp.status_code == 500


# ============================================
# Tests: GET /api/boxlite/tools
# ============================================

@pytest.mark.asyncio
async def test_get_available_tools(mock_boxlite_tools):
    """Get available tools returns tool list and definitions."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.get("/api/boxlite/tools")

    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    assert "definitions" in data
    assert "test_tool" in data["tools"]


# ============================================
# Tests: Authentication (verify_api_key import check)
# ============================================

@pytest.mark.asyncio
async def test_verify_api_key_is_imported():
    """verify_api_key is imported in routes module (not wired as Depends)."""
    from boxlite import routes
    assert hasattr(routes, "verify_api_key")


@pytest.mark.asyncio
async def test_routes_work_without_auth_dependency():
    """All routes currently work without auth middleware applied."""
    with patch("boxlite.routes.get_sandbox_manager") as mock_mgr:
        manager = make_manager()
        with patch.object(manager, "get_state_dict", return_value=mock_state_dict(manager)):
            mock_mgr.return_value = manager
            async with AsyncClient(
                transport=ASGITransport(app=create_test_app()),
                base_url="http://test",
            ) as client:
                resp = await client.get("/api/boxlite/sandbox/test-sandbox")

    assert resp.status_code == 200


# ============================================
# Tests: Reconnect endpoint
# ============================================

@pytest.mark.asyncio
async def test_reconnect_sandbox_not_found():
    """Reconnect to nonexistent sandbox returns 404."""
    with patch("boxlite.sandbox_manager._sandbox_managers", {}), \
         patch("boxlite.sandbox_manager.SINGLETON_MODE", False):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/reconnect",
                json={"sandbox_id": "nope"},
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reconnect_sandbox_success():
    """Reconnect to an existing sandbox returns 200."""
    manager = make_manager("existing-id")

    fake_managers = {"existing-id": manager}
    with patch("boxlite.sandbox_manager._sandbox_managers", fake_managers), \
         patch("boxlite.sandbox_manager.SINGLETON_MODE", False), \
         patch.object(manager, "reconnect", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/reconnect",
                json={"sandbox_id": "existing-id"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_id"] == "existing-id"


@pytest.mark.asyncio
async def test_reconnect_sandbox_singleton_no_sandbox():
    """Reconnect in singleton mode with no sandbox returns 404."""
    with patch("boxlite.sandbox_manager._sandbox_managers", {}), \
         patch("boxlite.sandbox_manager.SINGLETON_MODE", True), \
         patch("boxlite.sandbox_manager._singleton_sandbox_id", None):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/reconnect",
                json={"sandbox_id": "any-id"},
            )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reconnect_sandbox_singleton_with_existing():
    """Reconnect in singleton mode with existing sandbox returns 200."""
    manager = make_manager("singleton-id")

    fake_managers = {"singleton-id": manager}
    with patch("boxlite.sandbox_manager._sandbox_managers", fake_managers), \
         patch("boxlite.sandbox_manager.SINGLETON_MODE", True), \
         patch("boxlite.sandbox_manager._singleton_sandbox_id", "singleton-id"), \
         patch.object(manager, "reconnect", new_callable=AsyncMock):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/reconnect",
                json={"sandbox_id": "ignored-in-singleton"},
            )

    assert resp.status_code == 200
    data = resp.json()
    assert data["sandbox_id"] == "singleton-id"


@pytest.mark.asyncio
async def test_reconnect_sandbox_error():
    """Reconnect returns 500 when manager.reconnect raises."""
    manager = make_manager("err-id")

    fake_managers = {"err-id": manager}
    with patch("boxlite.sandbox_manager._sandbox_managers", fake_managers), \
         patch("boxlite.sandbox_manager.SINGLETON_MODE", False), \
         patch.object(manager, "reconnect", new_callable=AsyncMock, side_effect=Exception("reconnect fail")):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/boxlite/sandbox/reconnect",
                json={"sandbox_id": "err-id"},
            )

    assert resp.status_code == 500


# ============================================
# Tests: State includes files
# ============================================

@pytest.mark.asyncio
async def test_get_sandbox_state_includes_files(mock_get_sandbox_manager):
    """Sandbox state dict includes files field."""
    _, manager = mock_get_sandbox_manager

    state_dict = mock_state_dict(manager)
    state_dict["files"] = {"/index.html": "<html></html>"}

    with patch.object(manager, "get_state_dict", return_value=state_dict):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/boxlite/sandbox/test-sandbox")

    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data


# ============================================
# Tests: Concurrent operations
# ============================================

@pytest.mark.asyncio
async def test_concurrent_sandbox_operations(mock_get_sandbox_manager, mock_boxlite_tools):
    """Multiple endpoints can be called concurrently without conflict."""
    _, manager = mock_get_sandbox_manager

    with patch.object(manager, "get_state_dict", return_value=mock_state_dict(manager)):
        async with AsyncClient(
            transport=ASGITransport(app=create_test_app()),
            base_url="http://test",
        ) as client:
            results = await asyncio.gather(
                client.get("/api/boxlite/sandbox/test-sandbox"),
                client.get("/api/boxlite/sandbox/test-sandbox/files"),
                client.post(
                    "/api/boxlite/sandbox/test-sandbox/command",
                    json={"command": "echo 1"},
                ),
            )

    for resp in results:
        assert resp.status_code == 200


# ============================================
# Tests: Response model validation
# ============================================

@pytest.mark.asyncio
async def test_create_sandbox_response_shape(mock_get_sandbox_manager, mock_unregister_agent):
    """Create sandbox response has correct JSON shape."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post("/api/boxlite/sandbox")

    data = resp.json()
    # Verify all expected keys
    assert set(data.keys()) == {"sandbox_id", "status", "ws_url"}
    assert isinstance(data["sandbox_id"], str)
    assert isinstance(data["status"], str)
    assert isinstance(data["ws_url"], str)


@pytest.mark.asyncio
async def test_command_response_shape(mock_get_sandbox_manager):
    """Run command response has all expected fields."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/command",
            json={"command": "echo test"},
        )

    data = resp.json()
    expected_keys = {"success", "exit_code", "stdout", "stderr", "duration_ms"}
    assert expected_keys.issubset(data.keys())


@pytest.mark.asyncio
async def test_tool_response_shape(mock_get_sandbox_manager, mock_boxlite_tools):
    """Execute tool response has success, result, data fields."""
    async with AsyncClient(
        transport=ASGITransport(app=create_test_app()),
        base_url="http://test",
    ) as client:
        resp = await client.post(
            "/api/boxlite/sandbox/test-sandbox/tool",
            json={"tool_name": "test_tool", "params": {}},
        )

    data = resp.json()
    assert "success" in data
    assert "result" in data
    assert "data" in data
