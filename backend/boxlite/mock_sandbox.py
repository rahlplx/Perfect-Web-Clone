"""
Mock BoxLite Sandbox Manager

In-memory implementation for testing. No Docker/filesystem required.
Maintains type compatibility with real BoxLiteSandboxManager.
"""

from __future__ import annotations
import asyncio
from typing import Optional, Dict, List, Any
from pathlib import PurePosixPath

from .models import (
    SandboxState,
    SandboxStatus,
    FileEntry,
    CommandResult,
    TerminalSession,
    VisualSummary,
)


class MockBoxLiteSandboxManager:
    """
    In-memory sandbox for tests. Same interface as BoxLiteSandboxManager.
    """

    def __init__(self, sandbox_id: str = "mock"):
        self.sandbox_id = sandbox_id
        self._files: Dict[str, str] = {}
        self._state = SandboxState(
            sandbox_id=sandbox_id,
            status=SandboxStatus.RUNNING,
        )

    async def initialize(self, reset: bool = False) -> SandboxState:
        if reset:
            self._files.clear()
        return self._state

    async def write_file(self, path: str, content: str) -> bool:
        norm = self._norm(path)
        self._files[norm] = content
        return True

    async def read_file(self, path: str) -> Optional[str]:
        norm = self._norm(path)
        return self._files.get(norm)

    async def delete_file(self, path: str) -> bool:
        norm = self._norm(path)
        if norm in self._files:
            del self._files[norm]
            return True
        return False

    async def list_files(self, path: str = "/") -> List[FileEntry]:
        norm = self._norm(path)
        entries = []
        prefix = norm.rstrip("/") + "/"
        seen_dirs = set()

        for key in self._files:
            if key.startswith(prefix):
                rel = key[len(prefix):]
                parts = rel.split("/")
                if len(parts) == 1:
                    entries.append(FileEntry(
                        name=parts[0],
                        path=key,
                        type="file",
                        size=len(self._files[key]),
                    ))
                elif len(parts) > 1 and parts[0] not in seen_dirs:
                    seen_dirs.add(parts[0])
                    entries.append(FileEntry(
                        name=parts[0],
                        path=f"{prefix}{parts[0]}",
                        type="directory",
                        size=0,
                    ))
        return entries

    async def run_command(
        self,
        command: str,
        timeout: float = 60.0,
        cwd: Optional[str] = None,
        background: bool = False,
    ) -> CommandResult:
        # Simulate exit code for exit commands
        exit_code = 0
        if command.strip().startswith("exit "):
            try:
                exit_code = int(command.strip().split()[1])
            except (IndexError, ValueError):
                exit_code = 1

        return CommandResult(
            success=(exit_code == 0),
            stdout=f"mock: {command}" if exit_code == 0 else "",
            stderr=f"mock: {command}" if exit_code != 0 else "",
            exit_code=exit_code,
            duration_ms=0,
        )

    async def create_directory(self, path: str) -> bool:
        norm = self._norm(path)
        key = norm.rstrip("/") + "/.gitkeep"
        self._files[key] = ""
        return True

    async def rename_file(self, old_path: str, new_path: str) -> bool:
        old_norm = self._norm(old_path)
        new_norm = self._norm(new_path)
        if old_norm in self._files:
            self._files[new_norm] = self._files.pop(old_norm)
            return True
        return False

    async def start_dev_server(self) -> CommandResult:
        return CommandResult(
            success=True,
            stdout="Mock dev server started on port 8080",
            stderr="",
            exit_code=0,
            duration_ms=0,
        )

    async def stop_dev_server(self) -> bool:
        return True

    def get_state(self) -> SandboxState:
        return SandboxState(
            sandbox_id=self.sandbox_id,
            status=SandboxStatus.RUNNING,
            files=dict(self._files),
            terminals=[],
            preview_url="http://localhost:8080",
        )

    async def get_build_errors(self) -> list:
        return []

    async def get_visual_summary(self) -> VisualSummary:
        return VisualSummary(
            has_content=len(self._files) > 0,
            visible_element_count=0,
            text_preview="Mock sandbox",
        )

    async def cleanup(self):
        self._files.clear()

    def _norm(self, path: str) -> str:
        p = PurePosixPath(path)
        parts = [p.drive] if p.drive else []
        for part in p.parts[1:] if p.is_absolute() else p.parts:
            if part == "..":
                if len(parts) > 1:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        return "/" + "/".join(parts) if parts else "/"

    @property
    def work_dir(self):
        """Compat shim for fixtures that access work_dir"""
        return type("WorkDir", (), {"exists": lambda self: False, "mkdir": lambda self, **kw: None})()
