"""Framework-Specific Sandbox Templates.

Provides file templates for initializing sandbox environments
with the correct framework configuration.
"""

import json
from typing import Dict

import sys
import os
import importlib.util

# Import framework_config without triggering agent __init__
_spec = importlib.util.spec_from_file_location(
    "framework_config",
    os.path.join(os.path.dirname(__file__), "..", "agent", "framework_config.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

FrameworkType = _mod.FrameworkType
StylingType = _mod.StylingType
get_framework_config = _mod.get_framework_config
get_sandbox_template = _mod.get_sandbox_template


def get_framework_sandbox_files(framework: FrameworkType, styling: StylingType) -> Dict[str, str]:
    """Get complete sandbox file set for a framework.

    Returns a dictionary mapping file paths to their contents.
    These files should be written to the sandbox workspace.
    """
    return get_sandbox_template(framework, styling)


def get_framework_start_command(framework: FrameworkType) -> str:
    """Get the npm/node command to start the dev server."""
    commands = {
        FrameworkType.REACT: "npm run dev",
        FrameworkType.VUE: "npm run dev",
        FrameworkType.SVELTE: "npm run dev",
        FrameworkType.ASTRO: "npm run dev",
        FrameworkType.HTML: "npx vite",
        FrameworkType.NEXTJS: "npm run dev",
    }
    return commands[framework]


def get_framework_build_command(framework: FrameworkType) -> str:
    """Get the npm command to build for production."""
    commands = {
        FrameworkType.REACT: "npm run build",
        FrameworkType.VUE: "npm run build",
        FrameworkType.SVELTE: "npm run build",
        FrameworkType.ASTRO: "npm run build",
        FrameworkType.HTML: "npx vite build",
        FrameworkType.NEXTJS: "npm run build",
    }
    return commands[framework]


def get_framework_preview_command(framework: FrameworkType) -> str:
    """Get the npm command to preview production build."""
    commands = {
        FrameworkType.REACT: "npm run preview",
        FrameworkType.VUE: "npm run preview",
        FrameworkType.SVELTE: "npm run preview",
        FrameworkType.ASTRO: "npm run preview",
        FrameworkType.HTML: "npx vite preview",
        FrameworkType.NEXTJS: "npm start",
    }
    return commands[framework]


def get_framework_port(framework: FrameworkType) -> int:
    """Get the default dev server port."""
    ports = {
        FrameworkType.REACT: 5173,
        FrameworkType.VUE: 5173,
        FrameworkType.SVELTE: 5173,
        FrameworkType.ASTRO: 4321,
        FrameworkType.HTML: 5173,
        FrameworkType.NEXTJS: 3000,
    }
    return ports[framework]


def write_sandbox_files(workspace_path: str, files: Dict[str, str]) -> None:
    """Write template files to sandbox workspace.

    Args:
        workspace_path: Root path of the sandbox workspace
        files: Dictionary of file_path -> content
    """
    import os
    for file_path, content in files.items():
        full_path = os.path.join(workspace_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
