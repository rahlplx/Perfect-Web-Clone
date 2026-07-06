# Design Doc: Universal Cloning Engine — Hardening & Completion

## Problem
The Perfect Web Clone codebase has an incomplete universal framework conversion layer. While the core config/prompts/templates modules are complete (141 tests pass), there are **known residual issues**: hardcoded React/JSX assumptions in worker agent fallback paths, hardcoded `.jsx` extensions in MCP tools, docstring rot, and no reverse-engineering audit against mature OSS projects.

## Core Value Proposition
Deliver a **production-hardened, universally framework-aware cloning engine** by reverse-engineering mature OSS projects (language-mcp, web-cloner, repo2vec, codegen-lab) for battle-tested patterns, then applying those patterns to eliminate all React-hardcoded assumptions.

## MVP Scope
1. **Reverse-engineer 5+ OSS projects** — extract patterns for framework-agnostic code generation
2. **Audit all 33 backend Python files** — find every remaining React/JSX hardcode
3. **Mine solution patterns** — classify as applicable/not-applicable from OSS mining
4. **Fix all discovered issues** — framework-agnostic worker prompts, dynamic file extensions, docstrings
5. **Verify with expanded test suite** — 150+ tests covering framework-agnostic code paths

## Target Users
- Developers cloning websites to non-React frameworks (Vue, Svelte, Astro, HTML, Next.js)
- OSS maintainers relying on the project's universal cloning capability

## Success Metrics
- 0 React/JSX hardcodes in backend Python code
- All worker agent paths framework-aware (no fallback to React)
- Test suite passes at 150+ tests
- Patterns documented in `.vibe/learnings/`

## Technical Approach
1. **Phase A — Reverse Engineering Mining**: Search GitHub for OSS projects solving framework-agnostic code generation. Extract patterns.
2. **Phase B — Full Codebase Audit**: Recursive scan of all `.py` files for React/JSX/JS references.
3. **Phase C — Pattern Classification**: Map OSS patterns to our codebase gaps.
4. **Phase D — Implementation**: Fix all issues with TDD.
5. **Phase E — Verification**: 150+ tests, lint, typecheck.

## UI Requirements
No UI changes needed — this is backend hardening.

## Open Questions
- Which OSS repos have the most applicable patterns?
- How deep does the `worker_agent.py` refactoring need to go?
- Are there framework-specific issues in `task_contract.py` we haven't found?
