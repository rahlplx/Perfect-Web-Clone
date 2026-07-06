# Learned Patterns: Framework-Agnostic Refactor

## Pattern 1: Prompt-per-Stack Injection (from screenshot-to-code)

**Problem**: Worker agents need framework-specific conversion rules but share 90% common logic.

**Solution**:
```python
# framework_prompts.py
FRAMEWORK_WORKER_PROMPTS = {
    FrameworkType.REACT: REACT_WORKER_RULES,
    FrameworkType.VUE: VUE_WORKER_RULES,
    # ...
}

def get_framework_worker_prompt(framework: FrameworkType, styling: StylingType) -> str:
    base = BASE_WORKER_PROMPT
    framework_rules = FRAMEWORK_WORKER_PROMPTS.get(framework, REACT_WORKER_RULES)
    styling_rules = STYLING_RULES.get(styling, "")
    return f"{base}\n\n{framework_rules}\n\n{styling_rules}"
```

**Used in**: `agent/worker_agent.py:_build_system_prompt()`, `boxlite/worker_agent.py`

**Why it works**: Single base prompt, conditional injection per framework. No duplication.

---

## Pattern 2: Central Config as Single Source of Truth

**Problem**: File extensions, entry paths, allowed extensions scattered across 22 files.

**Solution**:
```python
# framework_config.py
@dataclass
class FrameworkConfig:
    framework: FrameworkType
    styling: StylingType
    file_extension: str        # .jsx, .vue, .svelte, .astro, .html, .tsx
    entry_path: str            # /src/main.jsx, /pages/index.tsx, etc.
    root_component_path: str   # /src/App.jsx, /App.vue, etc.
    allowed_extensions: List[str]
    forbidden_paths: List[str]
    shared_imports: List[str]
    package_dependencies: Dict[str, str]
    dev_dependencies: Dict[str, str]
    vite_plugin: str
    tailwind_config: Optional[str]
    index_html_template: str
```

**Used in**: All 22 modified files import from `framework_config.get_framework_config()`

**Why it works**: Change once, propagate everywhere. Type-safe via enums.

---

## Pattern 3: Spec-File Intermediate Representation (from ai-website-cloner)

**Problem**: Direct HTML → code generation is brittle across frameworks.

**Solution**:
```
HTML → Layout Spec (sections, positions, components) → Framework Code
```

**Implementation**: `agent/task_contract.py` `TaskContract` class holds:
- `sections: List[SectionSpec]` — layout-agnostic component specs
- `generate_root_component(framework, styling)` — framework-aware code gen
- `generate_entry_file(framework, styling)` — entry point per framework

**Why it works**: Spec is framework-agnostic. Generation is framework-specific. Clean separation.

---

## Pattern 4: Docstring Sweep for Terminology Consistency

**Problem**: "JSX conversion", "React components" littered in comments/docstrings across 18+ files.

**Solution**: Automated grep + manual edit pass:
```bash
grep -r "JSX\|React component\|jsx" --include="*.py" backend/
# Replace: "JSX" → "component file", "React component" → "UI component", "jsx" → "component"
```

**Files fixed**: 22 files, 18+ occurrences.

**Why it works**: Prevents cognitive load when reading Vue/Svelte code with React terminology.

---

## Pattern 5: Baseline Regression Tests First

**Problem**: Refactoring 22 files risks breaking React default.

**Solution**: Write `test_baseline_react.py` BEFORE any changes:
```python
def test_react_config_matches_original():
    config = get_framework_config(FrameworkType.REACT, StylingType.TAILWIND)
    assert config.file_extension == ".jsx"
    assert config.entry_path == "/src/main.jsx"
    assert config.root_component_path == "/src/App.jsx"
    # ... 9 tests total
```

**Result**: 141 tests pass after refactor. Zero regressions.

---

## Pattern 6: Subagent Parallel Dispatch with Worktrees (from GPT-Engineer)

**Problem**: S02-S04 independent but sequential would take 3x time.

**Solution**:
```
S02 (worker agents)     → Subagent A (worktree)
S03 (task contract)     → Subagent B (worktree)
S04 (boxlite + tools)   → Subagent C (worktree)
```

**Orchestration**: Parent agent creates `.vibe/handoff.md` per slice, launches subagents with specific prompts, merges on completion.

**Why it works**: True parallel execution. Each subagent gets clean context. Merge conflicts rare (different file sets).

---

## Anti-Patterns to Avoid

| Anti-Pattern | What Happened | Fix |
|--------------|---------------|-----|
| Hardcoding `.jsx` in boxlite | 2 MEDIUM review findings | Import `get_framework_config()` in boxlite layer |
| Single-agent sequential build | Would take 3 sessions | Parallel subagent dispatch |
| No baseline tests | Regression undetected | Write `test_baseline_*.py` FIRST |
| OSS mining AFTER fixing | Re-invented patterns | Mine 8 OSS projects FIRST (ADR-1) |