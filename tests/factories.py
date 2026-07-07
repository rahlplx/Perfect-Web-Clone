"""Test factory functions for agent_protocol types."""

import sys, os, importlib.util

_backend = os.path.join(os.path.dirname(__file__), '..', 'backend')
_proto = os.path.join(_backend, 'agent', 'agent_protocol.py')
_spec = importlib.util.spec_from_file_location('agent_protocol', _proto)
_mod = importlib.util.module_from_spec(_spec)
sys.modules['agent_protocol'] = _mod
_spec.loader.exec_module(_mod)

from agent_protocol import (
    WorkerReport, WorkerStatus, SpawnWorkersResult, ToolStatus,
    NextAction, create_shell_action, create_diagnose_action,
    create_screenshot_action, create_get_build_errors_action,
)


def make_worker_report(
    section_name: str = "hero",
    status: WorkerStatus = WorkerStatus.SUCCESS,
    files_created=None,
    message: str = "done",
    error=None,
    error_type=None,
    duration_ms: int = 100,
    iterations: int = 1,
    retry_count: int = 0,
) -> WorkerReport:
    return WorkerReport(
        section_name=section_name,
        status=status,
        files_created=files_created if files_created is not None else ["src/hero.tsx"],
        message=message,
        error=error,
        error_type=error_type,
        duration_ms=duration_ms,
        iterations=iterations,
        retry_count=retry_count,
    )


def make_spawn_workers_result(
    status: ToolStatus = ToolStatus.COMPLETE,
    workers_total: int = 2,
    workers_success: int = 2,
    workers_failed: int = 0,
    files_created=None,
    worker_reports=None,
    next_action=None,
    duration_ms: int = 500,
    errors=None,
) -> SpawnWorkersResult:
    return SpawnWorkersResult(
        status=status,
        workers_total=workers_total,
        workers_success=workers_success,
        workers_failed=workers_failed,
        files_created=files_created if files_created is not None else ["src/hero.tsx", "src/footer.tsx"],
        worker_reports=worker_reports if worker_reports is not None else [
            make_worker_report("hero"),
            make_worker_report("footer"),
        ],
        next_action=next_action,
        duration_ms=duration_ms,
        errors=errors if errors is not None else [],
    )
