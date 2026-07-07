from typing import Optional, List
from ports.sandbox import SandboxPort
from boxlite.mock_sandbox import MockBoxLiteSandboxManager
from boxlite.models import CommandResult, FileEntry, SandboxState

class MockSandboxAdapter:
    def __init__(self, sandbox_id: str = "mock-test"):
        self._sandbox = MockBoxLiteSandboxManager(sandbox_id=sandbox_id)
    
    async def initialize(self, reset: bool = False) -> SandboxState:
        return await self._sandbox.initialize(reset=reset)
    
    async def cleanup(self) -> None:
        await self._sandbox.cleanup()
    
    async def write_file(self, path: str, content: str) -> bool:
        return await self._sandbox.write_file(path, content)
    
    async def read_file(self, path: str) -> Optional[str]:
        return await self._sandbox.read_file(path)
    
    async def delete_file(self, path: str) -> bool:
        return await self._sandbox.delete_file(path)
    
    async def list_files(self, path: str = "/") -> List[FileEntry]:
        return await self._sandbox.list_files(path)
    
    async def run_command(self, command: str, timeout: float = 60.0, cwd: Optional[str] = None, background: bool = False) -> CommandResult:
        return await self._sandbox.run_command(command, timeout=timeout, cwd=cwd, background=background)
    
    async def start_dev_server(self) -> CommandResult:
        return await self._sandbox.start_dev_server()
    
    async def stop_dev_server(self) -> bool:
        return await self._sandbox.stop_dev_server()
    
    def get_state(self) -> SandboxState:
        return self._sandbox.get_state()
