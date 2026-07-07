"""
BaseMCPExecutor 测试

测试 base_executor.py 中的共享 execute() 路由和结果解析逻辑。

测试覆盖：
1. BaseMCPExecutor 初始化和 ABC 约束
2. execute() 路由：tuple / dict / string / None 返回值
3. _parse_special_result() 各种格式
4. _handle_unknown_tool() 默认行为
5. 工具注册和分发（通过 getattr 的 _execute_* 协议）
6. 错误处理：异常捕获

运行：
    cd backend
    pytest tests/test_base_executor.py -v
"""

import pytest
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.base_executor import BaseMCPExecutor


# ============================================
# 测试用的具体子类
# ============================================

class SimpleExecutor(BaseMCPExecutor):
    """基础测试子类 — 默认 unknown tool 返回 error tuple。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)


class TupleHandlerExecutor(BaseMCPExecutor):
    """返回 tuple 的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_echo(self, tool_input: Dict[str, Any]):
        return ("echo: " + str(tool_input.get("msg", "")), False)

    async def _execute_error(self, tool_input: Dict[str, Any]):
        return ("bad thing happened", True)

    async def _execute_empty(self, tool_input: Dict[str, Any]):
        return ("", False)


class DictHandlerExecutor(BaseMCPExecutor):
    """返回 dict 的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_dict_ok(self, tool_input: Dict[str, Any]):
        return {"result": "dict result", "is_error": False}

    async def _execute_dict_err(self, tool_input: Dict[str, Any]):
        return {"result": "failed op", "is_error": True}

    async def _execute_dict_no_flag(self, tool_input: Dict[str, Any]):
        return {"other_key": "no result key"}


class StringHandlerExecutor(BaseMCPExecutor):
    """返回 string 的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_hello(self, tool_input: Dict[str, Any]):
        return "hello world"

    async def _execute_err_prefix(self, tool_input: Dict[str, Any]):
        return "Error: something broke"

    async def _execute_action_fail(self, tool_input: Dict[str, Any]):
        return "[ACTION_FAILED] task failed"

    async def _execute_cmd_fail(self, tool_input: Dict[str, Any]):
        return "[COMMAND_FAILED] exit 1"

    async def _execute_mid_error(self, tool_input: Dict[str, Any]):
        return "Normal text with Error: inside"


class NoneHandlerExecutor(BaseMCPExecutor):
    """返回 None 的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_none(self, tool_input: Dict[str, Any]):
        return None


class ListHandlerExecutor(BaseMCPExecutor):
    """返回 list 的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_list(self, tool_input: Dict[str, Any]):
        return [1, 2, 3]


class ExceptionHandlerExecutor(BaseMCPExecutor):
    """抛出异常的处理器。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_value_err(self, tool_input: Dict[str, Any]):
        raise ValueError("something broke")

    async def _execute_runtime_err(self, tool_input: Dict[str, Any]):
        raise RuntimeError("runtime failure")

    async def _execute_generic_err(self, tool_input: Dict[str, Any]):
        raise Exception("generic error")


class SpecialResultExecutor(BaseMCPExecutor):
    """覆盖 _parse_special_result 的子类。"""

    def __init__(self, session_id: str = "test"):
        super().__init__(session_id)

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    def _parse_special_result(self, result: Any) -> Optional[Dict[str, Any]]:
        if isinstance(result, dict) and result.get("type") == "image":
            return {"content": [{"type": "image", "data": result.get("data", "")}], "is_error": False}
        if isinstance(result, list):
            items = [{"type": "text", "text": str(item)} for item in result]
            return {"content": items, "is_error": False}
        return None

    async def _execute_image(self, tool_input: Dict[str, Any]):
        return {"type": "image", "data": "base64data"}

    async def _execute_items(self, tool_input: Dict[str, Any]):
        return ["item1", "item2", "item3"]

    async def _execute_plain(self, tool_input: Dict[str, Any]):
        return "plain string"


class CustomUnknownExecutor(BaseMCPExecutor):
    """自定义 _handle_unknown_tool 返回值。"""

    def __init__(self, unknown_result: Any = ("Custom unknown", True)):
        super().__init__("custom-unknown")
        self._unknown_result = unknown_result

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return self._unknown_result

    def set_unknown_result(self, result):
        self._unknown_result = result


class InputCaptureExecutor(BaseMCPExecutor):
    """捕获 tool_input 用于断言。"""

    def __init__(self):
        super().__init__("capture")
        self.captured_input: Optional[Dict[str, Any]] = None

    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        return ("Unknown tool", True)

    async def _execute_capture(self, tool_input: Dict[str, Any]):
        self.captured_input = tool_input
        return ("captured", False)


# ============================================
# 1. 初始化测试
# ============================================

class TestBaseMCPExecutorInit:
    """测试 BaseMCPExecutor 初始化。"""

    def test_creates_instance_with_session_id(self):
        executor = SimpleExecutor("session-123")
        assert executor.session_id == "session-123"

    def test_initializes_state_attributes(self):
        executor = SimpleExecutor()
        assert executor._last_layout_sections == []
        assert executor._last_task_contracts == []
        assert executor._last_integration_plan is None
        assert executor._last_worker_results == {}
        assert executor._last_source_id == ""

    def test_cannot_instantiate_abc_directly(self):
        with pytest.raises(TypeError):
            BaseMCPExecutor("session")


# ============================================
# 2. execute() 路由 — tuple 返回值
# ============================================

class TestExecuteTupleReturn:
    """测试 execute() 处理 tuple 返回值。"""

    @pytest.mark.asyncio
    async def test_tuple_success(self):
        executor = TupleHandlerExecutor()
        result = await executor.execute("echo", {"msg": "hi"})

        assert result["content"][0]["text"] == "echo: hi"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_tuple_error(self):
        executor = TupleHandlerExecutor()
        result = await executor.execute("error", {})

        assert result["content"][0]["text"] == "bad thing happened"
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_tuple_empty_string(self):
        executor = TupleHandlerExecutor()
        result = await executor.execute("empty", {})

        assert result["content"][0]["text"] == ""
        assert result["is_error"] is False


# ============================================
# 3. execute() 路由 — dict 返回值
# ============================================

class TestExecuteDictReturn:
    """测试 execute() 处理 dict 返回值。"""

    @pytest.mark.asyncio
    async def test_dict_with_result_key(self):
        executor = DictHandlerExecutor()
        result = await executor.execute("dict_ok", {})

        assert result["content"][0]["text"] == "dict result"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_dict_with_error_flag(self):
        executor = DictHandlerExecutor()
        result = await executor.execute("dict_err", {})

        assert result["content"][0]["text"] == "failed op"
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_dict_without_result_key_falls_to_str(self):
        executor = DictHandlerExecutor()
        result = await executor.execute("dict_no_flag", {})

        assert "other_key" in result["content"][0]["text"]
        assert result["is_error"] is False


# ============================================
# 4. execute() 路由 — string 返回值
# ============================================

class TestExecuteStringReturn:
    """测试 execute() 处理 string 返回值。"""

    @pytest.mark.asyncio
    async def test_plain_string_success(self):
        executor = StringHandlerExecutor()
        result = await executor.execute("hello", {})

        assert result["content"][0]["text"] == "hello world"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_string_error_prefix(self):
        executor = StringHandlerExecutor()
        result = await executor.execute("err_prefix", {})

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_string_action_failed_prefix(self):
        executor = StringHandlerExecutor()
        result = await executor.execute("action_fail", {})

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_string_command_failed_prefix(self):
        executor = StringHandlerExecutor()
        result = await executor.execute("cmd_fail", {})

        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_non_starting_error_prefix_not_flagged(self):
        executor = StringHandlerExecutor()
        result = await executor.execute("mid_error", {})

        assert result["is_error"] is False


# ============================================
# 5. execute() 路由 — None 返回值
# ============================================

class TestExecuteNoneReturn:
    """测试 execute() 处理 None 返回值。"""

    @pytest.mark.asyncio
    async def test_none_result_returns_empty_string(self):
        executor = NoneHandlerExecutor()
        result = await executor.execute("none", {})

        assert result["content"][0]["text"] == ""
        assert result["is_error"] is False


# ============================================
# 6. execute() 路由 — list 返回值（非 tuple 非 dict）
# ============================================

class TestExecuteListReturn:
    """测试 execute() 处理 list 返回值。"""

    @pytest.mark.asyncio
    async def test_list_converted_to_str(self):
        executor = ListHandlerExecutor()
        result = await executor.execute("list", {})

        assert result["content"][0]["text"] == "[1, 2, 3]"
        assert result["is_error"] is False


# ============================================
# 7. _parse_special_result() 测试
# ============================================

class TestParseSpecialResult:
    """测试 _parse_special_result() 各种格式。"""

    @pytest.mark.asyncio
    async def test_default_returns_none(self):
        executor = SimpleExecutor()
        assert executor._parse_special_result("anything") is None

    @pytest.mark.asyncio
    async def test_image_type_triggers_special(self):
        executor = SpecialResultExecutor()
        result = await executor.execute("image", {})

        assert result["content"][0]["type"] == "image"
        assert result["content"][0]["data"] == "base64data"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_list_result_triggers_special(self):
        executor = SpecialResultExecutor()
        result = await executor.execute("items", {})

        assert len(result["content"]) == 3
        assert result["content"][0]["text"] == "item1"
        assert result["content"][1]["text"] == "item2"
        assert result["content"][2]["text"] == "item3"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_plain_string_not_special(self):
        executor = SpecialResultExecutor()
        result = await executor.execute("plain", {})

        assert result["content"][0]["text"] == "plain string"
        assert result["is_error"] is False


# ============================================
# 8. _handle_unknown_tool() 默认行为
# ============================================

class TestHandleUnknownTool:
    """测试 _handle_unknown_tool() 默认行为。"""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error_tuple(self):
        executor = SimpleExecutor()
        result = await executor.execute("nonexistent", {"input": "test"})

        assert result["content"][0]["text"] == "Unknown tool"
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_custom_string_result(self):
        executor = CustomUnknownExecutor("Tool not available")
        result = await executor.execute("missing", {})

        assert result["content"][0]["text"] == "Tool not available"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_unknown_tool_custom_dict_result(self):
        executor = CustomUnknownExecutor({"result": "not found", "is_error": True})
        result = await executor.execute("gone", {})

        assert result["content"][0]["text"] == "not found"
        assert result["is_error"] is True

    @pytest.mark.asyncio
    async def test_unknown_tool_custom_tuple_result(self):
        executor = CustomUnknownExecutor(("custom msg", True))
        result = await executor.execute("whatever", {})

        assert result["content"][0]["text"] == "custom msg"
        assert result["is_error"] is True


# ============================================
# 9. 工具注册和分发
# ============================================

class TestToolRegistrationDispatch:
    """测试工具注册和分发 — 通过 getattr 的 _execute_* 协议。"""

    @pytest.mark.asyncio
    async def test_execute_calls_matching_handler(self):
        executor = InputCaptureExecutor()
        await executor.execute("capture", {"param": 42})

        assert executor.captured_input == {"param": 42}

    @pytest.mark.asyncio
    async def test_multiple_tools_independent(self):
        executor = TupleHandlerExecutor()
        r1 = await executor.execute("echo", {"msg": "a"})
        r2 = await executor.execute("error", {})

        assert "echo: a" in r1["content"][0]["text"]
        assert "bad thing happened" in r2["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handler_receives_correct_input(self):
        executor = InputCaptureExecutor()
        await executor.execute("capture", {"x": 1, "y": 2, "z": 3})

        assert executor.captured_input == {"x": 1, "y": 2, "z": 3}


# ============================================
# 10. 错误处理 — 异常捕获
# ============================================

class TestErrorHandling:
    """测试错误处理：异常捕获。"""

    @pytest.mark.asyncio
    async def test_handler_exception_caught(self):
        executor = ExceptionHandlerExecutor()
        result = await executor.execute("value_err", {})

        assert result["is_error"] is True
        assert "something broke" in result["content"][0]["text"]
        assert result["content"][0]["text"].startswith("Error:")

    @pytest.mark.asyncio
    async def test_handler_runtime_error(self):
        executor = ExceptionHandlerExecutor()
        result = await executor.execute("runtime_err", {})

        assert result["is_error"] is True
        assert "runtime failure" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_handler_generic_exception(self):
        executor = ExceptionHandlerExecutor()
        result = await executor.execute("generic_err", {})

        assert result["is_error"] is True
        assert "generic error" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_sequential_exceptions_handled(self):
        executor = ExceptionHandlerExecutor()
        r1 = await executor.execute("value_err", {})
        r2 = await executor.execute("runtime_err", {})

        assert r1["is_error"] is True
        assert r2["is_error"] is True
        assert "something broke" in r1["content"][0]["text"]
        assert "runtime failure" in r2["content"][0]["text"]


# ============================================
# 11. 边界情况
# ============================================

class TestEdgeCases:
    """测试边界情况。"""

    @pytest.mark.asyncio
    async def test_empty_tool_input(self):
        executor = InputCaptureExecutor()
        await executor.execute("capture", {})

        assert executor.captured_input == {}

    @pytest.mark.asyncio
    async def test_large_tool_input(self):
        executor = InputCaptureExecutor()
        large = {"data": "x" * 10000}
        await executor.execute("capture", large)

        assert len(executor.captured_input["data"]) == 10000

    @pytest.mark.asyncio
    async def test_result_structure_always_valid(self):
        executor = TupleHandlerExecutor()
        result = await executor.execute("echo", {"msg": "test"})

        assert "content" in result
        assert "is_error" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) == 1
        assert "type" in result["content"][0]
        assert "text" in result["content"][0]

    @pytest.mark.asyncio
    async def test_special_result_before_tuple_parsing(self):
        """_parse_special_result 优先于 tuple 解析。"""
        executor = SpecialResultExecutor()
        result = await executor.execute("image", {})

        assert result["content"][0]["type"] == "image"
        assert result["is_error"] is False

    @pytest.mark.asyncio
    async def test_dict_without_is_error_defaults_false(self):
        executor = DictHandlerExecutor()
        result = await executor.execute("dict_no_flag", {})

        assert result["is_error"] is False
