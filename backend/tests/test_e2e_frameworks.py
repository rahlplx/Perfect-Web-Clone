"""E2E Tests for All Frameworks.

Tests that each framework produces valid configuration,
sandbox templates, and worker prompts.
"""

import os
import importlib.util
import json

import pytest

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
get_worker_conversion_rules = _mod.get_worker_conversion_rules
validate_framework_config = _mod.validate_framework_config

# Import framework_prompts
_spec2 = importlib.util.spec_from_file_location(
    "framework_prompts",
    os.path.join(os.path.dirname(__file__), "..", "agent", "framework_prompts.py"),
)
_mod2 = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(_mod2)
get_framework_worker_prompt = _mod2.get_framework_worker_prompt


class TestReactE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        required = ["package.json", "vite.config.js", "index.html", "src/main.jsx", "src/App.jsx"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "react" in pkg["dependencies"]
        assert "react-dom" in pkg["dependencies"]

    def test_worker_prompt_mentions_react(self):
        prompt = get_framework_worker_prompt(FrameworkType.REACT, StylingType.TAILWIND)
        assert "react" in prompt.lower()
        assert "jsx" in prompt.lower()

    def test_tailwind_includes_config(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "tailwind.config.js" in template
        assert "postcss.config.js" in template

    def test_css_modules_no_tailwind(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.CSS_MODULES)
        assert "tailwind.config.js" not in template
        assert "src/App.module.css" in template


class TestVueE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.VUE, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.VUE, StylingType.TAILWIND)
        required = ["package.json", "vite.config.js", "index.html", "src/main.js", "src/App.vue"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.VUE, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "vue" in pkg["dependencies"]

    def test_worker_prompt_mentions_vue(self):
        prompt = get_framework_worker_prompt(FrameworkType.VUE, StylingType.TAILWIND)
        assert "vue" in prompt.lower()
        assert "sfc" in prompt.lower() or "single file" in prompt.lower()


class TestSvelteE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.SVELTE, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.SVELTE, StylingType.TAILWIND)
        required = ["package.json", "vite.config.js", "index.html", "src/main.js", "src/App.svelte"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.SVELTE, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "svelte" in pkg["dependencies"]

    def test_worker_prompt_mentions_svelte(self):
        prompt = get_framework_worker_prompt(FrameworkType.SVELTE, StylingType.TAILWIND)
        assert "svelte" in prompt.lower()
        assert "{#" in prompt or "on:click" in prompt


class TestAstroE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.ASTRO, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.ASTRO, StylingType.TAILWIND)
        required = ["package.json", "astro.config.mjs", "src/pages/index.astro"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.ASTRO, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "astro" in pkg["dependencies"]

    def test_worker_prompt_mentions_astro(self):
        prompt = get_framework_worker_prompt(FrameworkType.ASTRO, StylingType.TAILWIND)
        assert "astro" in prompt.lower()
        assert "frontmatter" in prompt.lower() or "---" in prompt


class TestHtmlE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.HTML, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.HTML, StylingType.TAILWIND)
        required = ["package.json", "index.html", "src/style.css"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.HTML, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        # HTML might not have framework dependencies
        assert "name" in pkg

    def test_worker_prompt_mentions_html(self):
        prompt = get_worker_conversion_rules(FrameworkType.HTML)
        assert "html" in prompt.lower()
        assert "semantic" in prompt.lower() or "vanilla" in prompt.lower()


class TestNextJsE2E:
    def test_config_is_valid(self):
        config = get_framework_config(FrameworkType.NEXTJS, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_template_has_all_files(self):
        template = get_sandbox_template(FrameworkType.NEXTJS, StylingType.TAILWIND)
        required = ["package.json", "next.config.js", "pages/index.tsx", "tsconfig.json"]
        for f in required:
            assert f in template, f"Missing: {f}"

    def test_package_json_is_valid_json(self):
        template = get_sandbox_template(FrameworkType.NEXTJS, StylingType.TAILWIND)
        pkg = json.loads(template["package.json"])
        assert "next" in pkg["dependencies"]
        assert "react" in pkg["dependencies"]

    def test_worker_prompt_mentions_nextjs(self):
        prompt = get_framework_worker_prompt(FrameworkType.NEXTJS, StylingType.TAILWIND)
        assert "next" in prompt.lower()
        assert "server" in prompt.lower() or "app router" in prompt.lower()


class TestCrossFramework:
    """Tests that apply to all frameworks."""

    @pytest.mark.parametrize("framework", list(FrameworkType))
    def test_all_frameworks_have_valid_config(self, framework):
        for styling in StylingType:
            config = get_framework_config(framework, styling)
            assert validate_framework_config(config) is True

    @pytest.mark.parametrize("framework", list(FrameworkType))
    def test_all_frameworks_have_templates(self, framework):
        for styling in StylingType:
            template = get_sandbox_template(framework, styling)
            assert "package.json" in template
            assert isinstance(template, dict)

    @pytest.mark.parametrize("framework", list(FrameworkType))
    def test_all_frameworks_have_worker_rules(self, framework):
        rules = get_worker_conversion_rules(framework)
        assert len(rules) > 100  # Rules should be substantial

    @pytest.mark.parametrize("framework", list(FrameworkType))
    def test_all_frameworks_have_prompts(self, framework):
        for styling in StylingType:
            prompt = get_framework_worker_prompt(framework, styling)
            assert len(prompt) > 200  # Prompts should be substantial

    @pytest.mark.parametrize("styling", list(StylingType))
    def test_all_styling_options_work(self, styling):
        for framework in FrameworkType:
            config = get_framework_config(framework, styling)
            assert config.styling == styling
