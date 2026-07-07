"""Tests for task_contract module.

Covers:
- create_task_contract() factory function
- TaskContract dataclass fields and methods
- is_path_allowed() path validation
- generate_worker_prompt() for each framework type
- AcceptanceCriteria.validate()
- IntegrationPlan generation
- Edge cases: invalid frameworks, missing required fields
"""

from __future__ import annotations

import json
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.framework_config import FrameworkType, StylingType, get_framework_config
from agent.task_contract import (
    AcceptanceCriteria,
    ComponentEntry,
    EnhancedSectionData,
    FileDeliverable,
    ImageData,
    ImageRole,
    IntegrationPlan,
    LayoutProperties,
    LinkData,
    LinkType,
    SectionType,
    StyleProperties,
    TaskContract,
    TextContent,
    VisualProperties,
    create_integration_plan,
    create_task_contract,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_section_data(
    images=None,
    links=None,
    text_content=None,
    styles=None,
    raw_html="",
    css_rules="",
) -> dict:
    return {
        "images": images or [],
        "links": links or [],
        "text_content": text_content or {},
        "styles": styles or {},
        "raw_html": raw_html,
        "css_rules": css_rules,
    }


def _make_image(url="https://example.com/img.png", alt="img", **kw) -> dict:
    return {"url": url, "alt": alt, **kw}


def _make_link(url="https://example.com", text="link", **kw) -> dict:
    return {"url": url, "text": text, **kw}


# ===========================================================================
# 1. create_task_contract() factory
# ===========================================================================

class TestCreateTaskContract:
    def test_returns_task_contract(self):
        contract = create_task_contract(
            section_id="hero-0",
            section_type="hero",
            display_name="Hero",
            section_data=_make_section_data(),
        )
        assert isinstance(contract, TaskContract)

    def test_contract_id_derived_from_section_id(self):
        contract = create_task_contract(
            section_id="header-0",
            section_type="header",
            display_name="Header",
            section_data=_make_section_data(),
        )
        assert contract.contract_id == "header-0_contract"

    def test_worker_namespace_lowercased_and_sanitized(self):
        contract = create_task_contract(
            section_id="My.Component 1",
            section_type="content",
            display_name="Content",
            section_data=_make_section_data(),
        )
        assert contract.worker_namespace == "my-component-1"

    def test_priority_passed_through(self):
        contract = create_task_contract(
            section_id="a",
            section_type="section",
            display_name="A",
            section_data=_make_section_data(),
            priority=5,
        )
        assert contract.priority == 5

    def test_framework_and_styling_passed_through(self):
        contract = create_task_contract(
            section_id="a",
            section_type="section",
            display_name="A",
            section_data=_make_section_data(),
            framework_type=FrameworkType.VUE,
            styling_type=StylingType.PLAIN_CSS,
        )
        assert contract.framework_type == FrameworkType.VUE
        assert contract.styling_type == StylingType.PLAIN_CSS

    def test_invalid_section_type_falls_back_to_generic(self):
        contract = create_task_contract(
            section_id="x",
            section_type="nonexistent_type",
            display_name="X",
            section_data=_make_section_data(),
        )
        assert contract.section_data.section_type == SectionType.GENERIC

    def test_images_parsed_from_section_data(self):
        imgs = [_make_image(url="https://a.com/1.png"), _make_image(url="https://a.com/2.png")]
        contract = create_task_contract(
            section_id="gal-0",
            section_type="gallery",
            display_name="Gallery",
            section_data=_make_section_data(images=imgs),
        )
        assert len(contract.section_data.images) == 2
        assert contract.section_data.images[0].url == "https://a.com/1.png"

    def test_links_parsed_from_section_data(self):
        links = [_make_link(url="https://x.com"), _make_link(url="https://y.com")]
        contract = create_task_contract(
            section_id="nav-0",
            section_type="navigation",
            display_name="Nav",
            section_data=_make_section_data(links=links),
        )
        assert len(contract.section_data.links) == 2

    def test_string_images_still_parsed(self):
        contract = create_task_contract(
            section_id="s",
            section_type="section",
            display_name="S",
            section_data=_make_section_data(images=["https://img.png"]),
        )
        assert len(contract.section_data.images) == 1
        assert contract.section_data.images[0].url == "https://img.png"

    def test_string_links_still_parsed(self):
        contract = create_task_contract(
            section_id="s",
            section_type="section",
            display_name="S",
            section_data=_make_section_data(links=["https://link.com"]),
        )
        assert len(contract.section_data.links) == 1

    def test_acceptance_criteria_auto_populated(self):
        imgs = [_make_image(), _make_image(), _make_image()]
        links = [_make_link(), _make_link()]
        contract = create_task_contract(
            section_id="a",
            section_type="section",
            display_name="A",
            section_data=_make_section_data(images=imgs, links=links),
        )
        assert contract.acceptance.min_images == 3
        assert contract.acceptance.min_links == 2
        assert "ASection" in contract.acceptance.required_exports

    def test_raw_html_and_css_rules_captured(self):
        contract = create_task_contract(
            section_id="c",
            section_type="cta",
            display_name="CTA",
            section_data=_make_section_data(raw_html="<div>hi</div>", css_rules=".c{color:red}"),
        )
        assert contract.section_data.raw_html == "<div>hi</div>"
        assert contract.section_data.css_rules == ".c{color:red}"

    def test_styles_parsed(self):
        styles = {"colors": {"background": ["#fff"], "text": ["#000"], "accent": ["#f00"]}, "font_family": "Arial"}
        contract = create_task_contract(
            section_id="s",
            section_type="section",
            display_name="S",
            section_data=_make_section_data(styles=styles),
        )
        assert contract.section_data.styles.background_colors == ["#fff"]
        assert contract.section_data.styles.font_family == "Arial"


# ===========================================================================
# 2. TaskContract dataclass fields and methods
# ===========================================================================

class TestTaskContract:
    def test_default_framework_is_react(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert c.framework_type == FrameworkType.REACT

    def test_default_styling_is_tailwind(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert c.styling_type == StylingType.TAILWIND

    def test_default_deliverables_created_when_empty(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert len(c.deliverables) == 2
        assert c.deliverables[0].file_type == "component"
        assert c.deliverables[0].required is True

    def test_deliverables_not_overwritten_when_provided(self):
        custom = [FileDeliverable(path="Custom.jsx", file_type="component")]
        c = TaskContract(contract_id="x", worker_namespace="x", deliverables=custom)
        assert len(c.deliverables) == 1

    def test_namespace_to_component_name_simple(self):
        c = TaskContract(contract_id="x", worker_namespace="header")
        assert c._namespace_to_component_name() == "HeaderSection"

    def test_namespace_to_component_name_hyphenated(self):
        c = TaskContract(contract_id="x", worker_namespace="hero-0")
        assert c._namespace_to_component_name() == "Hero0Section"

    def test_namespace_to_component_name_already_has_section(self):
        c = TaskContract(contract_id="x", worker_namespace="my-section")
        assert c._namespace_to_component_name() == "MySection"

    def test_allowed_extensions(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert ".jsx" in c.allowed_extensions
        assert ".css" in c.allowed_extensions

    def test_forbidden_paths(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        fp = c.forbidden_paths
        assert "/src/main.jsx" in fp
        assert "/src/App.jsx" in fp

    def test_shared_imports(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert "import React from 'react'" in c.shared_imports

    def test_entry_path(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert c.entry_path == "/src/main.jsx"

    def test_root_component_path(self):
        c = TaskContract(contract_id="x", worker_namespace="x")
        assert c.root_component_path == "/src/App.jsx"

    def test_get_allowed_path(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        path = c.get_allowed_path("HeroSection.jsx")
        assert path == "/src/components/sections/hero/HeroSection.jsx"

    def test_to_dict(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        d = c.to_dict()
        assert d["contract_id"] == "x"
        assert d["worker_namespace"] == "hero"
        assert "scope" in d
        assert "deliverables" in d


# ===========================================================================
# 3. is_path_allowed() path validation
# ===========================================================================

class TestIsPathAllowed:
    def test_valid_path_allowed(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.jsx") is True

    def test_forbidden_path_rejected(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/main.jsx") is False

    def test_forbidden_app_path_rejected(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/App.jsx") is False

    def test_wrong_namespace_rejected(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/components/sections/footer/FooterSection.jsx") is False

    def test_invalid_extension_rejected(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.py") is False

    def test_path_without_leading_slash(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("src/components/sections/hero/HeroSection.jsx") is True

    def test_css_extension_allowed(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.css") is True

    def test_js_extension_allowed(self):
        c = TaskContract(contract_id="x", worker_namespace="hero")
        assert c.is_path_allowed("/src/components/sections/hero/utils.js") is True

    def test_vue_extensions(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.VUE,
        )
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.vue") is True
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.jsx") is False

    def test_svelte_extensions(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.SVELTE,
        )
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.svelte") is True

    def test_nextjs_extensions(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.NEXTJS,
        )
        assert c.is_path_allowed("/src/components/sections/hero/HeroSection.tsx") is True


# ===========================================================================
# 4. generate_worker_prompt() for each framework type
# ===========================================================================

class TestGenerateWorkerPrompt:
    @pytest.fixture
    def _base_contract(self):
        def _make(fw=FrameworkType.REACT, styling=StylingType.TAILWIND):
            imgs = [_make_image(url="https://img1.png"), _make_image(url="https://img2.png")]
            links = [_make_link(url="https://link1.com")]
            styles = {"colors": {"background": ["#fff"], "text": ["#000"], "accent": ["#f00"]}}
            return create_task_contract(
                section_id="hero-0",
                section_type="hero",
                display_name="Hero",
                section_data=_make_section_data(
                    images=imgs, links=links, styles=styles,
                    raw_html="<h1>Hello</h1>",
                    css_rules=".hero{color:blue}",
                ),
                framework_type=fw,
                styling_type=styling,
            )
        return _make

    def test_contains_contract_id(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "hero-0_contract" in prompt

    def test_contains_namespace(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "hero-0" in prompt

    def test_contains_component_name(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Hero0Section" in prompt

    def test_contains_images_section(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Images (2 total)" in prompt
        assert "img1.png" in prompt

    def test_contains_links_section(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Links (1 total)" in prompt
        assert "link1.com" in prompt

    def test_contains_colors_section(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Color Palette" in prompt
        assert "#fff" in prompt

    def test_contains_raw_html(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Reference HTML" in prompt

    def test_contains_css_rules(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Extracted CSS Rules" in prompt

    def test_react_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.REACT).generate_worker_prompt()
        assert "REACT" in prompt

    def test_vue_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.VUE).generate_worker_prompt()
        assert "VUE" in prompt

    def test_svelte_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.SVELTE).generate_worker_prompt()
        assert "SVELTE" in prompt

    def test_astro_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.ASTRO).generate_worker_prompt()
        assert "ASTRO" in prompt

    def test_html_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.HTML).generate_worker_prompt()
        assert "HTML" in prompt

    def test_nextjs_framework_label(self, _base_contract):
        prompt = _base_contract(FrameworkType.NEXTJS).generate_worker_prompt()
        assert "NEXTJS" in prompt

    def test_workflow_section_present(self, _base_contract):
        prompt = _base_contract().generate_worker_prompt()
        assert "Workflow" in prompt
        assert "query_section_data" in prompt

    def test_no_images_section_when_empty(self):
        c = create_task_contract(
            section_id="x", section_type="section", display_name="X",
            section_data=_make_section_data(),
        )
        prompt = c.generate_worker_prompt()
        assert "Images (0 total)" not in prompt

    def test_no_links_section_when_empty(self):
        c = create_task_contract(
            section_id="x", section_type="section", display_name="X",
            section_data=_make_section_data(),
        )
        prompt = c.generate_worker_prompt()
        assert "Links (0 total)" not in prompt


# ===========================================================================
# 5. AcceptanceCriteria.validate()
# ===========================================================================

class TestAcceptanceCriteria:
    def test_validate_returns_empty_when_passing(self):
        ac = AcceptanceCriteria(min_images=1, min_links=1)
        result = {"files": {"a": 'src="http://img.png" href="http://link.com"'}}
        warnings = ac.validate(result)
        assert warnings == []

    def test_validate_warns_on_missing_images(self):
        ac = AcceptanceCriteria(min_images=3)
        result = {"files": {"a": 'src="http://img.png"'}}
        warnings = ac.validate(result)
        assert any("images" in w.lower() for w in warnings)

    def test_validate_warns_on_missing_links(self):
        ac = AcceptanceCriteria(min_links=2)
        result = {"files": {"a": 'href="http://x.com"'}}
        warnings = ac.validate(result)
        assert any("links" in w.lower() for w in warnings)

    def test_validate_warns_on_missing_export(self):
        ac = AcceptanceCriteria(required_exports=["MyComponent"])
        result = {"files": {"a": "function App() {}"}}
        warnings = ac.validate(result)
        assert any("MyComponent" in w for w in warnings)

    def test_validate_passes_default_export(self):
        ac = AcceptanceCriteria(required_exports=["MyComponent"])
        result = {"files": {"a": "export default MyComponent"}}
        warnings = ac.validate(result)
        assert warnings == []

    def test_validate_passes_named_export(self):
        ac = AcceptanceCriteria(required_exports=["MyComponent"])
        result = {"files": {"a": "export { MyComponent }"}}
        warnings = ac.validate(result)
        assert warnings == []

    def test_validate_passes_function_export(self):
        ac = AcceptanceCriteria(required_exports=["MyComponent"])
        result = {"files": {"a": "export function MyComponent() {}"}}
        warnings = ac.validate(result)
        assert warnings == []

    def test_validate_empty_files(self):
        ac = AcceptanceCriteria(min_images=1, min_links=1)
        result = {"files": {}}
        warnings = ac.validate(result)
        assert len(warnings) == 2

    def test_validate_to_dict(self):
        ac = AcceptanceCriteria(min_images=2, min_links=3, required_exports=["X"])
        d = ac.to_dict()
        assert d["min_images"] == 2
        assert d["min_links"] == 3
        assert "X" in d["required_exports"]


# ===========================================================================
# 6. IntegrationPlan generation
# ===========================================================================

class TestIntegrationPlan:
    def _make_contract(self, section_type="hero", namespace="hero"):
        return create_task_contract(
            section_id=namespace,
            section_type=section_type,
            display_name="Hero",
            section_data=_make_section_data(),
        )

    def test_create_integration_plan_from_contracts(self):
        contracts = [self._make_contract("hero", "hero"), self._make_contract("footer", "footer")]
        plan = create_integration_plan(contracts, page_title="Test")
        assert isinstance(plan, IntegrationPlan)
        assert plan.page_title == "Test"
        assert len(plan.components) == 2

    def test_component_order_respects_section_type(self):
        contracts = [
            self._make_contract("footer", "footer"),
            self._make_contract("header", "header"),
            self._make_contract("hero", "hero"),
        ]
        plan = create_integration_plan(contracts)
        namespaces = [c.namespace for c in plan.components]
        assert namespaces[0] == "header"
        assert namespaces[1] == "hero"
        assert namespaces[2] == "footer"

    def test_framework_inherited_from_first_contract(self):
        contract = create_task_contract(
            section_id="a", section_type="section", display_name="A",
            section_data=_make_section_data(),
            framework_type=FrameworkType.VUE,
            styling_type=StylingType.PLAIN_CSS,
        )
        plan = create_integration_plan([contract])
        assert plan.framework_type == FrameworkType.VUE
        assert plan.styling_type == StylingType.PLAIN_CSS

    def test_empty_contracts(self):
        plan = create_integration_plan([])
        assert plan.components == []

    def test_generate_root_component_react(self):
        plan = IntegrationPlan(framework_type=FrameworkType.REACT)
        plan.components = [ComponentEntry("hero", "HeroSection", "./hero/HeroSection", "top")]
        code = plan.generate_root_component()
        assert "function App()" in code
        assert "HeroSection" in code
        assert "export default App" in code

    def test_generate_root_component_vue(self):
        plan = IntegrationPlan(framework_type=FrameworkType.VUE)
        plan.components = [ComponentEntry("hero", "HeroSection", "./hero/HeroSection", "top")]
        code = plan.generate_root_component()
        assert "<template>" in code
        assert "<script setup>" in code
        assert "HeroSection" in code

    def test_generate_root_component_svelte(self):
        plan = IntegrationPlan(framework_type=FrameworkType.SVELTE)
        plan.components = [ComponentEntry("hero", "HeroSection", "./hero/HeroSection", "top")]
        code = plan.generate_root_component()
        assert "<script>" in code
        assert "HeroSection" in code

    def test_generate_root_component_astro(self):
        plan = IntegrationPlan(framework_type=FrameworkType.ASTRO)
        plan.components = [ComponentEntry("hero", "HeroSection", "./hero/HeroSection", "top")]
        code = plan.generate_root_component()
        assert "---" in code
        assert "import HeroSection" in code

    def test_generate_root_component_html(self):
        plan = IntegrationPlan(framework_type=FrameworkType.HTML, page_title="My Page")
        code = plan.generate_root_component()
        assert "<!DOCTYPE html>" in code
        assert "My Page" in code

    def test_generate_root_component_nextjs(self):
        plan = IntegrationPlan(framework_type=FrameworkType.NEXTJS)
        plan.components = [ComponentEntry("hero", "HeroSection", "./hero/HeroSection", "top")]
        code = plan.generate_root_component()
        assert "import React from 'react'" in code
        assert "function App()" in code

    def test_generate_index_css(self):
        plan = IntegrationPlan(css_variables={"--primary": "#f00", "--font": "Arial"})
        css = plan.generate_index_css()
        assert ":root" in css
        assert "--primary: #f00" in css
        assert "body" in css

    def test_generate_index_css_no_variables(self):
        plan = IntegrationPlan()
        css = plan.generate_index_css()
        assert "No variables extracted" in css

    def test_generate_entry_file_react(self):
        plan = IntegrationPlan(framework_type=FrameworkType.REACT)
        entry = plan.generate_entry_file()
        assert "ReactDOM" in entry

    def test_generate_entry_file_vue(self):
        plan = IntegrationPlan(framework_type=FrameworkType.VUE)
        entry = plan.generate_entry_file()
        assert "createApp" in entry

    def test_generate_entry_file_svelte(self):
        plan = IntegrationPlan(framework_type=FrameworkType.SVELTE)
        entry = plan.generate_entry_file()
        assert "new App" in entry

    def test_generate_entry_file_nextjs(self):
        plan = IntegrationPlan(framework_type=FrameworkType.NEXTJS)
        entry = plan.generate_entry_file()
        assert "AppProps" in entry

    def test_generate_entry_file_astro_returns_empty(self):
        plan = IntegrationPlan(framework_type=FrameworkType.ASTRO)
        assert plan.generate_entry_file() == ""

    def test_generate_entry_file_html(self):
        plan = IntegrationPlan(framework_type=FrameworkType.HTML)
        entry = plan.generate_entry_file()
        assert "index.css" in entry

    def test_generate_package_json_react(self):
        plan = IntegrationPlan(framework_type=FrameworkType.REACT)
        pkg = json.loads(plan.generate_package_json())
        assert "react" in pkg["dependencies"]
        assert pkg["type"] == "module"

    def test_generate_package_json_nextjs(self):
        plan = IntegrationPlan(framework_type=FrameworkType.NEXTJS)
        pkg = json.loads(plan.generate_package_json())
        assert "next" in pkg["dependencies"]
        assert pkg["scripts"]["dev"] == "next dev"

    def test_generate_vite_config_react(self):
        plan = IntegrationPlan(framework_type=FrameworkType.REACT)
        config = plan.generate_vite_config()
        assert "plugin-react" in config

    def test_generate_vite_config_vue(self):
        plan = IntegrationPlan(framework_type=FrameworkType.VUE)
        config = plan.generate_vite_config()
        assert "plugin-vue" in config

    def test_generate_vite_config_svelte(self):
        plan = IntegrationPlan(framework_type=FrameworkType.SVELTE)
        config = plan.generate_vite_config()
        assert "vite-plugin-svelte" in config

    def test_generate_vite_config_nextjs_returns_empty(self):
        plan = IntegrationPlan(framework_type=FrameworkType.NEXTJS)
        assert plan.generate_vite_config() == ""

    def test_generate_vite_config_astro_returns_empty(self):
        plan = IntegrationPlan(framework_type=FrameworkType.ASTRO)
        assert plan.generate_vite_config() == ""

    def test_global_styles_for_react_tailwind(self):
        assert IntegrationPlan._global_styles_for(FrameworkType.REACT, StylingType.TAILWIND) == "/src/index.css"

    def test_global_styles_for_astro(self):
        assert IntegrationPlan._global_styles_for(FrameworkType.ASTRO, StylingType.TAILWIND) == ""

    def test_global_styles_for_nextjs(self):
        assert IntegrationPlan._global_styles_for(FrameworkType.NEXTJS, StylingType.TAILWIND) == "/styles/globals.css"

    def test_global_styles_for_vue(self):
        result = IntegrationPlan._global_styles_for(FrameworkType.VUE, StylingType.TAILWIND)
        assert result == "/src/style.css"

    def test_to_dict(self):
        plan = IntegrationPlan(page_title="Test", source_url="https://example.com")
        plan.components = [ComponentEntry("hero", "H", "./h", "top")]
        d = plan.to_dict()
        assert d["metadata"]["page_title"] == "Test"
        assert len(d["component_order"]) == 1


# ===========================================================================
# 7. Edge cases
# ===========================================================================

class TestEdgeCases:
    def test_vue_deliverables_extension(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.VUE,
        )
        exts = [d.path for d in c.deliverables]
        assert any(".vue" in p for p in exts)

    def test_svelte_deliverables_extension(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.SVELTE,
        )
        exts = [d.path for d in c.deliverables]
        assert any(".svelte" in p for p in exts)

    def test_nextjs_deliverables_extension(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.NEXTJS,
        )
        exts = [d.path for d in c.deliverables]
        assert any(".tsx" in p for p in exts)

    def test_astro_deliverables_extension(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.ASTRO,
        )
        exts = [d.path for d in c.deliverables]
        assert any(".astro" in p for p in exts)

    def test_html_deliverables_extension(self):
        c = TaskContract(
            contract_id="x", worker_namespace="hero",
            framework_type=FrameworkType.HTML,
        )
        exts = [d.path for d in c.deliverables]
        assert any(".html" in p for p in exts)

    def test_no_section_data_deliverables_still_created(self):
        c = TaskContract(contract_id="x", worker_namespace="hero", section_data=None)
        assert len(c.deliverables) == 2

    def test_empty_section_id(self):
        c = TaskContract(contract_id="", worker_namespace="")
        assert c.worker_namespace == ""
        assert c._namespace_to_component_name() == "Section"

    def test_file_deliverable_to_dict(self):
        fd = FileDeliverable(path="a.jsx", file_type="component", required=True)
        d = fd.to_dict()
        assert d["path"] == "a.jsx"
        assert d["required"] is True

    def test_image_data_to_dict(self):
        img = ImageData(url="https://x.png", alt="test", role=ImageRole.LOGO)
        d = img.to_dict()
        assert d["url"] == "https://x.png"
        assert d["role"] == "logo"

    def test_link_data_to_dict(self):
        link = LinkData(url="https://x.com", text="click", link_type=LinkType.CTA)
        d = link.to_dict()
        assert d["url"] == "https://x.com"
        assert d["type"] == "cta"

    def test_visual_properties_to_dict(self):
        vp = VisualProperties(rect={"x": 0, "y": 0, "width": 100, "height": 50})
        d = vp.to_dict()
        assert d["rect"]["width"] == 100

    def test_style_properties_to_dict(self):
        sp = StyleProperties(background_colors=["#fff"], font_family="Arial")
        d = sp.to_dict()
        assert "#fff" in d["colors"]["background"]

    def test_text_content_to_dict(self):
        tc = TextContent(headings=["H1"], paragraphs=["p1"])
        d = tc.to_dict()
        assert "H1" in d["headings"]

    def test_layout_properties_to_dict(self):
        lp = LayoutProperties(flex_direction="row", child_count=3)
        d = lp.to_dict()
        assert d["flex_direction"] == "row"
        assert d["child_count"] == 3

    def test_enhanced_section_data_to_dict(self):
        esd = EnhancedSectionData(
            section_id="s1", section_type=SectionType.HERO, display_name="Hero"
        )
        d = esd.to_dict()
        assert d["section_id"] == "s1"
        assert d["section_type"] == "hero"

    def test_component_entry_to_dict(self):
        ce = ComponentEntry("hero", "Hero", "./hero", "top")
        d = ce.to_dict()
        assert d["namespace"] == "hero"
        assert d["position"] == "top"

    def test_image_role_enum(self):
        assert ImageRole.LOGO.value == "logo"
        assert ImageRole.PHOTO.value == "photo"

    def test_link_type_enum(self):
        assert LinkType.NAVIGATION.value == "navigation"
        assert LinkType.CTA.value == "cta"

    def test_section_type_enum(self):
        assert SectionType.HEADER.value == "header"
        assert SectionType.HERO.value == "hero"

    def test_create_task_contract_minimal(self):
        c = create_task_contract(
            section_id="x", section_type="section", display_name="X",
            section_data={},
        )
        assert c.contract_id == "x_contract"
        assert len(c.deliverables) == 2

    def test_create_integration_plan_inherits_global_styles(self):
        contract = create_task_contract(
            section_id="a", section_type="section", display_name="A",
            section_data=_make_section_data(),
            framework_type=FrameworkType.VUE,
            styling_type=StylingType.TAILWIND,
        )
        plan = create_integration_plan([contract])
        assert plan.global_styles == "/src/style.css"
