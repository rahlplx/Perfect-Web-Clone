"""TDD Tests for Framework Config Module."""

import sys
import os
import importlib.util

import pytest

# Bypass backend.agent.__init__.py eager imports
_spec = importlib.util.spec_from_file_location(
    "framework_config",
    os.path.join(os.path.dirname(__file__), "..", "agent", "framework_config.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

FrameworkType = _mod.FrameworkType
StylingType = _mod.StylingType
FrameworkConfig = _mod.FrameworkConfig
get_framework_config = _mod.get_framework_config
get_sandbox_template = _mod.get_sandbox_template
get_worker_conversion_rules = _mod.get_worker_conversion_rules
validate_framework_config = _mod.validate_framework_config
ALLOWED_VITE_PLUGINS = _mod.ALLOWED_VITE_PLUGINS
KNOWN_SAFE_PACKAGES = _mod.KNOWN_SAFE_PACKAGES


class TestFrameworkType:
    def test_react_exists(self):
        assert FrameworkType.REACT.value == "react"

    def test_vue_exists(self):
        assert FrameworkType.VUE.value == "vue"

    def test_svelte_exists(self):
        assert FrameworkType.SVELTE.value == "svelte"

    def test_astro_exists(self):
        assert FrameworkType.ASTRO.value == "astro"

    def test_html_exists(self):
        assert FrameworkType.HTML.value == "html"

    def test_nextjs_exists(self):
        assert FrameworkType.NEXTJS.value == "nextjs"

    def test_all_frameworks_count(self):
        assert len(FrameworkType) == 6


class TestStylingType:
    def test_tailwind_exists(self):
        assert StylingType.TAILWIND.value == "tailwind"

    def test_css_modules_exists(self):
        assert StylingType.CSS_MODULES.value == "css_modules"

    def test_plain_css_exists(self):
        assert StylingType.PLAIN_CSS.value == "plain_css"

    def test_all_styling_count(self):
        assert len(StylingType) == 3


class TestFrameworkConfig:
    def test_config_has_framework_field(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        assert config.framework == FrameworkType.REACT

    def test_config_has_styling_field(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        assert config.styling == StylingType.TAILWIND

    def test_config_has_file_extension(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        assert config.file_extension == ".jsx"

    def test_config_has_vite_plugin(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        assert config.vite_plugin == "@vitejs/plugin-react"

    def test_config_has_package_dependencies(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        assert isinstance(config.package_dependencies, dict)


class TestGetFrameworkConfig:
    def test_react_tailwind(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert config.framework == FrameworkType.REACT
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".jsx"
        assert config.vite_plugin == "@vitejs/plugin-react"

    def test_react_css_modules(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.CSS_MODULES)
        assert config.framework == FrameworkType.REACT
        assert config.styling == StylingType.CSS_MODULES
        assert config.file_extension == ".jsx"

    def test_react_plain_css(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.PLAIN_CSS)
        assert config.framework == FrameworkType.REACT
        assert config.styling == StylingType.PLAIN_CSS
        assert config.file_extension == ".jsx"

    def test_vue_tailwind(self):
        config = get_framework_config(FrameworkType.VUE, StylingType.TAILWIND)
        assert config.framework == FrameworkType.VUE
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".vue"
        assert config.vite_plugin == "@vitejs/plugin-vue"

    def test_vue_css_modules(self):
        config = get_framework_config(FrameworkType.VUE, StylingType.CSS_MODULES)
        assert config.framework == FrameworkType.VUE
        assert config.file_extension == ".vue"

    def test_svelte_tailwind(self):
        config = get_framework_config(FrameworkType.SVELTE, StylingType.TAILWIND)
        assert config.framework == FrameworkType.SVELTE
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".svelte"
        assert config.vite_plugin == "@sveltejs/vite-plugin-svelte"

    def test_svelte_plain_css(self):
        config = get_framework_config(FrameworkType.SVELTE, StylingType.PLAIN_CSS)
        assert config.framework == FrameworkType.SVELTE
        assert config.file_extension == ".svelte"

    def test_astro_tailwind(self):
        config = get_framework_config(FrameworkType.ASTRO, StylingType.TAILWIND)
        assert config.framework == FrameworkType.ASTRO
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".astro"
        assert config.vite_plugin is None

    def test_astro_plain_css(self):
        config = get_framework_config(FrameworkType.ASTRO, StylingType.PLAIN_CSS)
        assert config.framework == FrameworkType.ASTRO
        assert config.file_extension == ".astro"

    def test_html_tailwind(self):
        config = get_framework_config(FrameworkType.HTML, StylingType.TAILWIND)
        assert config.framework == FrameworkType.HTML
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".html"
        assert config.vite_plugin is None

    def test_html_plain_css(self):
        config = get_framework_config(FrameworkType.HTML, StylingType.PLAIN_CSS)
        assert config.framework == FrameworkType.HTML
        assert config.file_extension == ".html"

    def test_nextjs_tailwind(self):
        config = get_framework_config(FrameworkType.NEXTJS, StylingType.TAILWIND)
        assert config.framework == FrameworkType.NEXTJS
        assert config.styling == StylingType.TAILWIND
        assert config.file_extension == ".tsx"
        assert config.vite_plugin is None

    def test_nextjs_css_modules(self):
        config = get_framework_config(FrameworkType.NEXTJS, StylingType.CSS_MODULES)
        assert config.framework == FrameworkType.NEXTJS
        assert config.file_extension == ".tsx"


class TestGetSandboxTemplate:
    def test_react_template_has_package_json(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "package.json" in template
        assert isinstance(template["package.json"], str)

    def test_react_template_has_vite_config(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "vite.config.js" in template

    def test_react_template_has_index_html(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "index.html" in template

    def test_react_template_has_entry_point(self):
        template = get_sandbox_template(FrameworkType.REACT, StylingType.TAILWIND)
        assert "src/main.jsx" in template

    def test_vue_template_has_entry_point(self):
        template = get_sandbox_template(FrameworkType.VUE, StylingType.TAILWIND)
        assert "src/main.js" in template

    def test_svelte_template_has_entry_point(self):
        template = get_sandbox_template(FrameworkType.SVELTE, StylingType.TAILWIND)
        assert "src/main.js" in template

    def test_astro_template_has_config(self):
        template = get_sandbox_template(FrameworkType.ASTRO, StylingType.TAILWIND)
        assert "astro.config.mjs" in template

    def test_html_template_has_index(self):
        template = get_sandbox_template(FrameworkType.HTML, StylingType.TAILWIND)
        assert "index.html" in template

    def test_nextjs_template_has_pages(self):
        template = get_sandbox_template(FrameworkType.NEXTJS, StylingType.TAILWIND)
        assert "pages/index.tsx" in template

    def test_tailwind_templates_have_config(self):
        for framework in FrameworkType:
            template = get_sandbox_template(framework, StylingType.TAILWIND)
            assert "tailwind.config.js" in template
            assert "postcss.config.js" in template

    def test_non_tailwind_templates_no_tailwind_config(self):
        for framework in FrameworkType:
            template = get_sandbox_template(framework, StylingType.PLAIN_CSS)
            assert "tailwind.config.js" not in template


class TestGetWorkerConversionRules:
    def test_react_rules_mention_jsx(self):
        rules = get_worker_conversion_rules(FrameworkType.REACT)
        assert "jsx" in rules.lower() or "JSX" in rules

    def test_react_rules_mention_classname(self):
        rules = get_worker_conversion_rules(FrameworkType.REACT)
        assert "className" in rules

    def test_react_rules_mention_hooks(self):
        rules = get_worker_conversion_rules(FrameworkType.REACT)
        assert "useState" in rules or "useEffect" in rules or "hooks" in rules.lower()

    def test_vue_rules_mention_sfc(self):
        rules = get_worker_conversion_rules(FrameworkType.VUE)
        assert "sfc" in rules.lower() or ".vue" in rules or "single file" in rules.lower()

    def test_vue_rules_mention_reactive(self):
        rules = get_worker_conversion_rules(FrameworkType.VUE)
        assert "reactive" in rules.lower() or "ref" in rules.lower() or "computed" in rules.lower()

    def test_svelte_rules_mention_syntax(self):
        rules = get_worker_conversion_rules(FrameworkType.SVELTE)
        assert "{#" in rules or "svelte" in rules.lower() or "on:click" in rules

    def test_astro_rules_mention_frontmatter(self):
        rules = get_worker_conversion_rules(FrameworkType.ASTRO)
        assert "---" in rules or "frontmatter" in rules.lower() or "astro" in rules.lower()

    def test_astro_rules_mention_islands(self):
        rules = get_worker_conversion_rules(FrameworkType.ASTRO)
        assert "client:" in rules or "island" in rules.lower() or "hydrate" in rules.lower()

    def test_html_rules_mention_semantic(self):
        rules = get_worker_conversion_rules(FrameworkType.HTML)
        assert "semantic" in rules.lower() or "html5" in rules.lower() or "section" in rules.lower()

    def test_html_rules_mention_no_framework(self):
        rules = get_worker_conversion_rules(FrameworkType.HTML)
        assert "no framework" in rules.lower() or "vanilla" in rules.lower() or "plain" in rules.lower()

    def test_nextjs_rules_mention_app_router(self):
        rules = get_worker_conversion_rules(FrameworkType.NEXTJS)
        assert "app router" in rules.lower() or "next.js" in rules.lower() or "nextjs" in rules.lower()

    def test_nextjs_rules_mention_server_components(self):
        rules = get_worker_conversion_rules(FrameworkType.NEXTJS)
        assert "server" in rules.lower() or "ssr" in rules.lower() or "use client" in rules


class TestSecurityValidation:
    def test_allowed_vite_plugins_exists(self):
        assert ALLOWED_VITE_PLUGINS is not None
        assert isinstance(ALLOWED_VITE_PLUGINS, (list, set, frozenset))

    def test_react_plugin_allowed(self):
        assert "@vitejs/plugin-react" in ALLOWED_VITE_PLUGINS

    def test_vue_plugin_allowed(self):
        assert "@vitejs/plugin-vue" in ALLOWED_VITE_PLUGINS

    def test_svelte_plugin_allowed(self):
        assert "@sveltejs/vite-plugin-svelte" in ALLOWED_VITE_PLUGINS

    def test_none_plugin_allowed(self):
        assert None in ALLOWED_VITE_PLUGINS

    def test_known_safe_packages_exists(self):
        assert KNOWN_SAFE_PACKAGES is not None
        assert isinstance(KNOWN_SAFE_PACKAGES, (list, set, frozenset))

    def test_react_in_safe_packages(self):
        assert "react" in KNOWN_SAFE_PACKAGES

    def test_vue_in_safe_packages(self):
        assert "vue" in KNOWN_SAFE_PACKAGES

    def test_svelte_in_safe_packages(self):
        assert "svelte" in KNOWN_SAFE_PACKAGES

    def test_tailwind_in_safe_packages(self):
        assert "tailwindcss" in KNOWN_SAFE_PACKAGES

    def test_validate_config_valid(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert validate_framework_config(config) is True

    def test_validate_config_rejects_invalid_plugin(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="malicious-plugin",
            package_dependencies={"dependencies": {}, "devDependencies": {}},
        )
        with pytest.raises(ValueError, match="Plugin not allowed"):
            validate_framework_config(config)

    def test_validate_config_rejects_unsafe_package(self):
        config = FrameworkConfig(
            framework=FrameworkType.REACT,
            styling=StylingType.TAILWIND,
            file_extension=".jsx",
            vite_plugin="@vitejs/plugin-react",
            package_dependencies={
                "dependencies": {"malicious-package": "^1.0.0"},
                "devDependencies": {},
            },
        )
        with pytest.raises(ValueError, match="Package not allowed"):
            validate_framework_config(config)


class TestEdgeCases:
    def test_invalid_framework_raises_error(self):
        with pytest.raises((ValueError, KeyError, TypeError)):
            get_framework_config("invalid", StylingType.TAILWIND)

    def test_invalid_styling_raises_error(self):
        with pytest.raises((ValueError, KeyError, TypeError)):
            get_framework_config(FrameworkType.REACT, "invalid")

    def test_config_is_hashable(self):
        config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert hash(config) is not None

    def test_configs_are_deterministic(self):
        config1 = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        config2 = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
        assert config1.framework == config2.framework
        assert config1.file_extension == config2.file_extension
