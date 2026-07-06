"""
BoxLite 测试配置文件

这个文件包含 pytest fixtures（测试夹具）。
Fixtures 是测试的"准备工作"——在测试运行前创建所需的对象和环境。

关键概念：
- @pytest.fixture：标记一个函数为 fixture
- scope="function"：每个测试函数运行时都重新创建（默认）
- scope="module"：整个测试文件共享一个实例
- scope="session"：整个测试会话共享一个实例
"""

import pytest
import asyncio
import sys
import os
import shutil
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from boxlite.sandbox_manager import BoxLiteSandboxManager
from boxlite.mock_sandbox import MockBoxLiteSandboxManager


# ============================================
# Event Loop Config
# ============================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================
# Sandbox Fixtures
# ============================================

@pytest.fixture
def sandbox_id():
    import uuid
    return f"test-sandbox-{uuid.uuid4().hex[:8]}"


@pytest.fixture
async def sandbox(sandbox_id):
    """Sandbox fixture using in-memory mock (no Docker/filesystem needed)"""
    manager = MockBoxLiteSandboxManager(sandbox_id)
    await manager.initialize(reset=True)
    yield manager
    await manager.cleanup()


@pytest.fixture
async def mock_sandbox():
    """In-memory mock sandbox (no Docker/filesystem needed)"""
    manager = MockBoxLiteSandboxManager("mock-test")
    await manager.initialize(reset=True)
    yield manager
    await manager.cleanup()


@pytest.fixture
async def sandbox_with_files(sandbox):
    await sandbox.write_file("/test.txt", "Hello World\nLine 2\nLine 3")
    await sandbox.write_file("/src/app.js", """
function main() {
    console.log("Hello");
    return 42;
}

export default main;
""".strip())
    await sandbox.write_file("/src/utils.js", """
export function add(a, b) {
    return a + b;
}

export function multiply(a, b) {
    return a * b;
}
""".strip())
    return sandbox


# ============================================
# Helper Functions
# ============================================

def assert_tool_success(result):
    """
    断言工具执行成功。

    使用方式：
    ```python
    result = await write_file(...)
    assert_tool_success(result)
    ```
    """
    assert result.success, f"Tool failed: {result.result}"


def assert_tool_failure(result, error_contains=None):
    """
    断言工具执行失败。

    使用方式：
    ```python
    result = await read_file("/nonexistent", sandbox)
    assert_tool_failure(result, "not found")
    ```
    """
    assert not result.success, f"Tool should have failed but succeeded: {result.result}"
    if error_contains:
        assert error_contains.lower() in result.result.lower(), \
            f"Error message should contain '{error_contains}', got: {result.result}"
