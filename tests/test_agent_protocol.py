"""Comprehensive tests for agent.agent_protocol."""

import sys, os, importlib.util

_backend = os.path.join(os.path.dirname(__file__), '..', 'backend')
_proto = os.path.join(_backend, 'agent', 'agent_protocol.py')
_spec = importlib.util.spec_from_file_location('agent_protocol', _proto)
_mod = importlib.util.module_from_spec(_spec)
sys.modules['agent_protocol'] = _mod
_spec.loader.exec_module(_mod)

import json
import pytest
from factories import make_worker_report, make_spawn_workers_result

from agent_protocol import (
    ToolStatus, WorkerStatus,
    WorkerReport, SpawnWorkersResult, NextAction,
    create_shell_action, create_diagnose_action,
    create_screenshot_action, create_get_build_errors_action,
    build_spawn_workers_result,
)


# ============================================
# WorkerReport
# ============================================

class TestWorkerReport:
    def test_defaults(self):
        wr = WorkerReport(section_name="x", status=WorkerStatus.SUCCESS)
        assert wr.files_created == []
        assert wr.message == ""
        assert wr.error is None
        assert wr.error_type is None
        assert wr.duration_ms == 0
        assert wr.iterations == 0
        assert wr.retry_count == 0

    def test_full_construction(self):
        wr = WorkerReport(
            section_name="hero", status=WorkerStatus.FAILED,
            files_created=["a.tsx"], message="oops",
            error="boom", error_type="compilation",
            duration_ms=42, iterations=3, retry_count=1,
        )
        assert wr.section_name == "hero"
        assert wr.status == WorkerStatus.FAILED
        assert wr.files_created == ["a.tsx"]
        assert wr.message == "oops"
        assert wr.error == "boom"
        assert wr.duration_ms == 42

    def test_to_dict_success(self):
        wr = make_worker_report(section_name="nav", status=WorkerStatus.SUCCESS, files_created=["a"])
        d = wr.to_dict()
        assert d["section"] == "nav"
        assert d["status"] == "success"
        assert d["files"] == ["a"]
        assert d["error"] is None

    def test_to_dict_failed(self):
        wr = make_worker_report(status=WorkerStatus.FAILED, error="err msg")
        d = wr.to_dict()
        assert d["status"] == "failed"
        assert d["error"] == "err msg"

    def test_to_dict_empty_files(self):
        wr = make_worker_report(files_created=[])
        assert wr.to_dict()["files"] == []

    def test_to_dict_special_characters(self):
        wr = make_worker_report(section_name="§pecial™", message="日本語テスト")
        d = wr.to_dict()
        assert d["section"] == "§pecial™"
        assert d["message"] == "日本語テスト"

    def test_factory_make_worker_report(self):
        wr = make_worker_report()
        assert wr.section_name == "hero"
        assert wr.status == WorkerStatus.SUCCESS

    def test_multiple_files(self):
        wr = make_worker_report(files_created=["a.tsx", "b.css", "c.ts"])
        assert len(wr.files_created) == 3

    def test_to_dict_json_serializable(self):
        wr = make_worker_report()
        json.dumps(wr.to_dict())  # must not raise

    def test_timeout_status(self):
        wr = WorkerReport(section_name="t", status=WorkerStatus.TIMEOUT)
        d = wr.to_dict()
        assert d["status"] == "timeout"


# ============================================
# NextAction
# ============================================

class TestNextAction:
    def test_defaults(self):
        na = NextAction()
        assert na.required is True
        assert na.tool == ""
        assert na.params == {}
        assert na.reason == ""

    def test_to_dict(self):
        na = NextAction(required=False, tool="shell", params={"cmd": "ls"}, reason="test")
        d = na.to_dict()
        assert d["required"] is False
        assert d["tool"] == "shell"
        assert d["params"] == {"cmd": "ls"}
        assert d["reason"] == "test"

    def test_to_instruction_no_tool(self):
        assert NextAction(tool="").to_instruction() == ""

    def test_to_instruction_no_params(self):
        assert NextAction(tool="screenshot").to_instruction() == "screenshot()"

    def test_to_instruction_with_string_params(self):
        na = NextAction(tool="shell", params={"command": "npm test"})
        assert na.to_instruction() == 'shell(command="npm test")'

    def test_to_instruction_with_mixed_params(self):
        na = NextAction(tool="shell", params={"command": "ls", "background": True})
        result = na.to_instruction()
        assert "shell(" in result
        assert 'command="ls"' in result
        assert "background=True" in result

    def test_to_dict_json_serializable(self):
        na = NextAction(tool="x", params={"k": [1, 2]})
        json.dumps(na.to_dict())


# ============================================
# Factory Functions
# ============================================

class TestFactoryFunctions:
    def test_create_shell_action(self):
        a = create_shell_action("npm install", background=False, reason="deps")
        assert a.tool == "shell"
        assert a.params["command"] == "npm install"
        assert a.params["background"] is False
        assert a.reason == "deps"
        assert a.required is True

    def test_create_shell_action_defaults(self):
        a = create_shell_action("ls")
        assert a.params["background"] is True
        assert a.reason == "Execute shell command"

    def test_create_diagnose_action(self):
        a = create_diagnose_action()
        assert a.tool == "diagnose_preview_state"
        assert a.reason == "Check for build or runtime errors"

    def test_create_diagnose_action_custom_reason(self):
        a = create_diagnose_action("custom")
        assert a.reason == "custom"

    def test_create_screenshot_action(self):
        a = create_screenshot_action()
        assert a.tool == "take_screenshot"
        assert a.reason == "Verify the visual result"

    def test_create_screenshot_action_custom_reason(self):
        a = create_screenshot_action("visual check")
        assert a.reason == "visual check"

    def test_create_get_build_errors_action(self):
        a = create_get_build_errors_action()
        assert a.tool == "get_build_errors"
        assert "compilation" in a.reason.lower()

    def test_create_get_build_errors_action_custom_reason(self):
        a = create_get_build_errors_action("check errors")
        assert a.reason == "check errors"


# ============================================
# SpawnWorkersResult
# ============================================

class TestSpawnWorkersResult:
    def test_defaults(self):
        r = SpawnWorkersResult(status=ToolStatus.COMPLETE)
        assert r.workers_total == 0
        assert r.files_created == []
        assert r.worker_reports == []
        assert r.next_action is None
        assert r.duration_ms == 0
        assert r.errors == []

    def test_to_dict_basic(self):
        r = make_spawn_workers_result()
        d = r.to_dict()
        assert d["tool_status"] == "complete"
        assert d["result"]["workers_total"] == 2
        assert d["result"]["workers_success"] == 2
        assert d["result"]["files_created"] == ["src/hero.tsx", "src/footer.tsx"]
        assert d["result"]["duration_ms"] == 500
        assert len(d["worker_reports"]) == 2
        assert d["next_action"] is None
        assert d["errors"] is None

    def test_to_dict_with_next_action(self):
        a = create_get_build_errors_action("check")
        r = make_spawn_workers_result(next_action=a)
        d = r.to_dict()
        assert d["next_action"]["tool"] == "get_build_errors"

    def test_to_dict_with_errors(self):
        r = make_spawn_workers_result(errors=["err1", "err2"])
        d = r.to_dict()
        assert d["errors"] == ["err1", "err2"]

    def test_to_dict_partial_status(self):
        r = make_spawn_workers_result(status=ToolStatus.PARTIAL, workers_success=1, workers_failed=1)
        assert r.to_dict()["tool_status"] == "partial"

    def test_to_dict_failed_status(self):
        r = make_spawn_workers_result(status=ToolStatus.FAILED)
        assert r.to_dict()["tool_status"] == "failed"

    def test_to_dict_in_progress_status(self):
        r = make_spawn_workers_result(status=ToolStatus.IN_PROGRESS)
        assert r.to_dict()["tool_status"] == "in_progress"

    def test_to_agent_message_complete(self):
        r = make_spawn_workers_result()
        msg = r.to_agent_message()
        assert "TOOL COMPLETE: spawn_section_workers" in msg
        assert "2/2 successful" in msg
        assert "Files created: 2" in msg

    def test_to_agent_message_partial(self):
        r = make_spawn_workers_result(status=ToolStatus.PARTIAL, workers_success=1, workers_total=2, workers_failed=1)
        msg = r.to_agent_message()
        assert "TOOL PARTIAL" in msg
        assert "1/2 succeeded" in msg

    def test_to_agent_message_failed(self):
        r = make_spawn_workers_result(status=ToolStatus.FAILED, workers_success=0, workers_failed=2)
        msg = r.to_agent_message()
        assert "TOOL FAILED" in msg

    def test_to_agent_message_worker_reports(self):
        w1 = make_worker_report("nav", WorkerStatus.SUCCESS, files_created=["a"])
        w2 = make_worker_report("hero", WorkerStatus.FAILED, files_created=[])
        r = make_spawn_workers_result(worker_reports=[w1, w2], workers_total=2, workers_success=1, workers_failed=1, status=ToolStatus.PARTIAL)
        msg = r.to_agent_message()
        assert "✓ nav" in msg
        assert "✗ hero" in msg

    def test_to_agent_message_errors(self):
        r = make_spawn_workers_result(errors=["compile failed"])
        msg = r.to_agent_message()
        assert "Errors:" in msg
        assert "compile failed" in msg

    def test_to_agent_message_no_worker_reports(self):
        r = make_spawn_workers_result(worker_reports=[])
        msg = r.to_agent_message()
        assert "Worker Reports:" not in msg

    def test_to_agent_message_json_serializable_dict(self):
        r = make_spawn_workers_result()
        json.dumps(r.to_dict())


# ============================================
# build_spawn_workers_result
# ============================================

class _FakeWorkerResult:
    """Minimal mock for WorkerResult from worker_agent.py."""
    def __init__(self, section_name, success, files=None, summary="", error=None,
                 error_type="none", duration_ms=0, iterations=0, retry_count=0):
        self.worker_id = f"worker-{section_name}"
        self.section_name = section_name
        self.success = success
        self.files = files or {}
        self.summary = summary
        self.error = error
        self.error_type = error_type
        self.duration_ms = duration_ms
        self.iterations = iterations
        self.retry_count = retry_count


class TestBuildSpawnWorkersResult:
    def test_all_success(self):
        wr1 = _FakeWorkerResult("hero", True, files={"a.tsx": "code"}, duration_ms=100, iterations=2, retry_count=0)
        wr2 = _FakeWorkerResult("footer", True, files={"b.tsx": "code"}, duration_ms=80, iterations=1, retry_count=0)
        result = build_spawn_workers_result([wr1, wr2], ["a.tsx", "b.tsx"], 200)
        assert result.status == ToolStatus.COMPLETE
        assert result.workers_total == 2
        assert result.workers_success == 2
        assert result.workers_failed == 0
        assert len(result.worker_reports) == 2
        assert result.worker_reports[0].status == WorkerStatus.SUCCESS
        assert result.next_action is not None
        assert result.next_action.tool == "get_build_errors"

    def test_all_failed(self):
        wr = _FakeWorkerResult("hero", False, error="crash")
        result = build_spawn_workers_result([wr], [], 50)
        assert result.status == ToolStatus.FAILED
        assert result.workers_failed == 1
        assert result.next_action is None

    def test_partial_success(self):
        wr1 = _FakeWorkerResult("hero", True, files={"a.tsx": "c"})
        wr2 = _FakeWorkerResult("nav", False, error="fail")
        result = build_spawn_workers_result([wr1, wr2], ["a.tsx"], 100)
        assert result.status == ToolStatus.PARTIAL
        assert result.workers_success == 1
        assert result.workers_failed == 1
        assert result.next_action is not None

    def test_timeout_detection(self):
        wr = _FakeWorkerResult("hero", False, error="timeout after 30s")
        result = build_spawn_workers_result([wr], [], 30)
        assert result.workers_failed == 1
        assert result.worker_reports[0].status == WorkerStatus.TIMEOUT

    def test_empty_results(self):
        result = build_spawn_workers_result([], [], 0)
        assert result.status == ToolStatus.COMPLETE
        assert result.workers_total == 0

    def test_worker_report_files(self):
        wr = _FakeWorkerResult("hero", True, files={"a.tsx": "1", "b.tsx": "2"})
        result = build_spawn_workers_result([wr], ["a.tsx", "b.tsx"], 10)
        assert result.worker_reports[0].files_created == ["a.tsx", "b.tsx"]

    def test_worker_summary_default(self):
        wr = _FakeWorkerResult("hero", True, summary="")
        result = build_spawn_workers_result([wr], [], 10)
        assert result.worker_reports[0].message == "Component created"

    def test_worker_summary_used(self):
        wr = _FakeWorkerResult("hero", True, summary="Built hero section")
        result = build_spawn_workers_result([wr], [], 10)
        assert result.worker_reports[0].message == "Built hero section"

    def test_worker_error_message_default(self):
        wr = _FakeWorkerResult("hero", False, summary="", error="oops")
        result = build_spawn_workers_result([wr], [], 10)
        assert result.worker_reports[0].message == "Failed"

    def test_errors_param(self):
        result = build_spawn_workers_result([], [], 0, errors=["mgr err"])
        assert result.errors == ["mgr err"]

    def test_errors_default_none(self):
        result = build_spawn_workers_result([], [], 0)
        assert result.errors == []


# ============================================
# Edge Cases
# ============================================

class TestEdgeCases:
    def test_worker_report_empty_section_name(self):
        wr = WorkerReport(section_name="", status=WorkerStatus.SUCCESS)
        assert wr.to_dict()["section"] == ""

    def test_worker_report_none_error_fields(self):
        wr = WorkerReport(section_name="x", status=WorkerStatus.SUCCESS, error=None, error_type=None)
        d = wr.to_dict()
        assert d["error"] is None

    def test_spawn_workers_result_empty_lists(self):
        r = SpawnWorkersResult(status=ToolStatus.COMPLETE, files_created=[], worker_reports=[], errors=[])
        d = r.to_dict()
        assert d["result"]["files_created"] == []
        assert d["worker_reports"] == []
        assert d["errors"] is None

    def test_next_action_empty_params(self):
        na = NextAction(tool="shell", params={})
        assert na.to_instruction() == "shell()"

    def test_shell_action_special_chars(self):
        a = create_shell_action("echo 'hello; rm -rf /'")
        assert a.params["command"] == "echo 'hello; rm -rf /'"

    def test_spawn_result_large_counts(self):
        r = make_spawn_workers_result(workers_total=1000, workers_success=999, workers_failed=1)
        d = r.to_dict()
        assert d["result"]["workers_total"] == 1000

    def test_negative_duration(self):
        wr = WorkerReport(section_name="x", status=WorkerStatus.SUCCESS, duration_ms=-1)
        assert wr.duration_ms == -1

    def test_to_dict_and_back_roundtrip(self):
        r = make_spawn_workers_result(next_action=create_get_build_errors_action("reason"))
        d = r.to_dict()
        json_str = json.dumps(d)
        loaded = json.loads(json_str)
        assert loaded["tool_status"] == "complete"
        assert loaded["next_action"]["tool"] == "get_build_errors"
