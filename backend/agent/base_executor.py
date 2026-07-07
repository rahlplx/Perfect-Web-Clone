"""
Base MCP Tool Executor

Shared execute() routing and result parsing for WebContainer and BoxLite executors.

Hexagonal Architecture:
  This implements the executor/driven-adapter pattern.
  Tool handlers are driven adapters; the execute() method is the port interface.
"""

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseMCPExecutor(ABC):
    """
    Template Method for MCP tool execution.

    Subclass must implement:
    - _execute_{tool_name}(input) handlers
    - _handle_unknown_tool(name, input) for custom unknown tool behavior
    - _parse_special_result(result) for image/list content handling
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._last_layout_sections: list = []
        self._last_task_contracts: list = []
        self._last_integration_plan = None
        self._last_worker_results: Dict[str, Dict[str, Any]] = {}
        self._last_source_id: str = ""

    @abstractmethod
    def _handle_unknown_tool(self, tool_name: str, tool_input: Dict[str, Any]):
        """Handle unknown tool - return error tuple or special result"""
        ...

    def _parse_special_result(self, result: Any) -> Optional[Dict[str, Any]]:
        """Override to handle image/list content types. Return None for default handling."""
        return None

    async def execute(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a tool. Shared routing logic.

        Returns:
            {"content": [{"type": "text", "text": "..."}], "is_error": bool}
        """
        logger.info(f"Executing tool: {tool_name}")

        try:
            handler = getattr(self, f"_execute_{tool_name}", None)

            if handler:
                result = await handler(tool_input)
            else:
                result = self._handle_unknown_tool(tool_name, tool_input)

            # Check for special content types first
            special = self._parse_special_result(result)
            if special is not None:
                return special

            # Parse result - support multiple return formats
            if isinstance(result, tuple) and len(result) == 2:
                result_text, is_error = result
            elif isinstance(result, dict) and "result" in result:
                result_text = result.get("result", "")
                is_error = result.get("is_error", False)
            else:
                result_text = str(result) if result else ""
                is_error = (
                    isinstance(result_text, str) and
                    (result_text.startswith("Error:") or
                     result_text.startswith("[ACTION_FAILED]") or
                     result_text.startswith("[COMMAND_FAILED]"))
                )

            return {
                "content": [{"type": "text", "text": result_text}],
                "is_error": is_error,
            }

        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True,
            }
