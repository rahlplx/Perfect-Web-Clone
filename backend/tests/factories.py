"""
Factory functions for test data creation.
Provides deterministic, configurable test objects.
"""

from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


def make_worker_config(
    name: str = "test-worker",
    namespace: str = "test",
    max_retries: int = 3,
    timeout: float = 300.0,
    **overrides,
) -> Dict[str, Any]:
    """Create a BaseWorkerConfig-compatible dict."""
    return {
        "name": name,
        "namespace": namespace,
        "max_retries": max_retries,
        "timeout": timeout,
        **overrides,
    }


def make_worker_result(
    success: bool = True,
    worker_name: str = "test-worker",
    section_name: str = "test-section",
    status: str = "completed",
    output: str = "test output",
    error: Optional[str] = None,
    **overrides,
) -> Dict[str, Any]:
    """Create a BaseWorkerResult-compatible dict."""
    return {
        "success": success,
        "worker_name": worker_name,
        "section_name": section_name,
        "status": status,
        "output": output,
        "error": error,
        **overrides,
    }


def make_task_contract(
    namespace: str = "test",
    section_name: str = "test-section",
    section_type: str = "component",
    framework: str = "react",
    styling: str = "tailwind",
    **overrides,
) -> Dict[str, Any]:
    """Create a TaskContract-compatible dict."""
    return {
        "namespace": namespace,
        "section_name": section_name,
        "section_type": section_type,
        "framework": framework,
        "styling": styling,
        "source_url": f"https://example.com/{section_name}",
        "output_dir": f"/output/{namespace}/{section_name}",
        "acceptance_criteria": {
            "has_component": True,
            "has_styles": True,
            "has_tests": False,
        },
        **overrides,
    }


def make_spawn_workers_result(
    workers: Optional[List[Dict[str, Any]]] = None,
    total_sections: int = 1,
    **overrides,
) -> Dict[str, Any]:
    """Create a SpawnWorkersResult-compatible dict."""
    if workers is None:
        workers = [
            {
                "section_name": "test-section",
                "section_type": "component",
                "status": "pending",
                "worker_id": f"worker-{uuid.uuid4().hex[:8]}",
            }
        ]
    return {
        "workers": workers,
        "total_sections": total_sections,
        "spawned_count": len(workers),
        **overrides,
    }


def make_worker_report(
    section_name: str = "test-section",
    status: str = "completed",
    worker_id: Optional[str] = None,
    **overrides,
) -> Dict[str, Any]:
    """Create a WorkerReport-compatible dict."""
    return {
        "section_name": section_name,
        "status": status,
        "worker_id": worker_id or f"worker-{uuid.uuid4().hex[:8]}",
        "output": "test output",
        "files_created": [],
        "errors": [],
        **overrides,
    }


def make_sandbox_state(
    sandbox_id: Optional[str] = None,
    status: str = "running",
    **overrides,
) -> Dict[str, Any]:
    """Create a SandboxState-compatible dict."""
    return {
        "sandbox_id": sandbox_id or f"sandbox-{uuid.uuid4().hex[:8]}",
        "status": status,
        "created_at": "2024-01-01T00:00:00Z",
        "files": [],
        "terminals": [],
        **overrides,
    }


def make_command_result(
    success: bool = True,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    **overrides,
) -> Dict[str, Any]:
    """Create a CommandResult-compatible dict."""
    return {
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "duration_ms": 100,
        **overrides,
    }


def make_file_entry(
    name: str = "test.txt",
    path: str = "/test.txt",
    is_dir: bool = False,
    size: int = 100,
    **overrides,
) -> Dict[str, Any]:
    """Create a FileEntry-compatible dict."""
    return {
        "name": name,
        "path": path,
        "is_dir": is_dir,
        "size": size,
        "modified_at": "2024-01-01T00:00:00Z",
        **overrides,
    }


def make_cache_entry(
    url: str = "https://example.com",
    html: str = "<html></html>",
    title: str = "Test Page",
    **overrides,
) -> Dict[str, Any]:
    """Create a cache entry-compatible dict."""
    return {
        "url": url,
        "html": html,
        "title": title,
        "cached_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-02T00:00:00Z",
        **overrides,
    }


def make_llm_message(
    role: str = "user",
    content: str = "Hello",
    **overrides,
) -> Dict[str, Any]:
    """Create an LLM message-compatible dict."""
    return {
        "role": role,
        "content": content,
        **overrides,
    }


def make_tool_definition(
    name: str = "test_tool",
    description: str = "A test tool",
    input_schema: Optional[Dict[str, Any]] = None,
    **overrides,
) -> Dict[str, Any]:
    """Create a tool definition-compatible dict."""
    return {
        "name": name,
        "description": description,
        "input_schema": input_schema or {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            },
        },
        **overrides,
    }
