"""Baseline Regression Test for React Framework."""

import os
import importlib.util

import pytest

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
get_worker_conversion_rules = _mod.get_worker_conversion_rules


class TestReactBaseline:
    def test_react_config_matches_original(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert config.framework == FrameworkType.REACT
        assert config.file_extension == ".jsx"
        assert config.vite_plugin == "@vitejs/plugin-react"

    def test_react_sandbox_has_required_files(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        required_files = [
            "package.json",
            "vite.config.js",
            "index.html",
            "src/main.jsx",
            "src/App.jsx",
        ]
        for file in required_files:
            assert file in template, f"Missing required file: {file}"

    def test_react_package_json_has_correct_deps(self):
        import json
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "react" in pkg["dependencies"]
        assert "react-dom" in pkg["dependencies"]

    def test_react_worker_rules_include_jsx_conversion(self):
        rules = get_worker_conversion_rules(FrameworkType.REACT)
        assert "className" in rules
        assert "jsx" in rules.lower()

    def test_react_tailwind_includes_config_files(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "tailwind.config.js" in template
        assert "postcss.config.js" in template
        assert "src/index.css" in template

    def test_react_css_modules_no_tailwind_config(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.CSS_MODULES)
        assert "tailwind.config.js" not in template
        assert "src/App.module.css" in template

    def test_react_plain_css_no_tailwind_config(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.PLAIN_CSS)
        assert "tailwind.config.js" not in template
        assert "src/App.css" in template

    def test_react_vite_config_uses_react_plugin(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "@vitejs/plugin-react" in template["vite.config.js"]

    def test_react_main_jsx_imports_react(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "import React" in template["src/main.jsx"]
        assert "ReactDOM" in template["src/main.jsx"]
