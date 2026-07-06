# Retro: Framework-Agnostic Hardening (2026-07-07)

## What Happened

**Goal**: Transform React-only website cloner → universal 6-framework engine (React, Vue, Svelte, Astro, HTML, Next.js) × 3 styling = 18 combos

**Phases Completed**:
1. **Think** — Design doc approved via boardroom review
2. **Plan** — GSD milestones/slices created (M001: 4 slices)
3. **Break** — S01-S04 decomposed to atomic tasks
4. **Build** — S01-S04 dispatched to subagents, all completed
5. **Harness** — Production readiness checks (3/6 PASS, 1 FAIL rate limiting)
6. **Review** — Multi-perspective audit (0 CRITICAL, 2 MEDIUM)
7. **Ship** — Commit + PR #3

## What Went Well

| Pattern | Why It Worked |
|---------|---------------|
| OSS mining BEFORE fixing (ADR-1) | Found 3 mature patterns in 8 projects, avoided reinventing |
| Worker agent prompt injection | Clean separation: base prompt + framework-specific rules |
| Dynamic extension resolution | Single source of truth in `file_extension` in `framework_config.py` |
| Docstring sweep (ADR-4) | Caught 18+ "JSX/React" references in comments |
| TDD baseline tests first | `test_baseline_react.py` prevented regression during refactor |
| Subagent parallel dispatch | S02-S04 ran concurrently, 45 files changed in single session |

## What Didn't Go Well

| Issue | Impact | Root Cause |
|-------|--------|------------|
| 2 MEDIUM review findings in boxlite | Non-React frameworks get .jsx extensions | BoxLite layer wasn't fully migrated (uses sandbox.framework attr only) |
| Pre-existing 46 test failures | BoxLite sandbox fixture missing | Requires running BoxLite service — CI gap |
| LSP errors persist | Python 3.14 typing changes | Anthropic SDK + pydantic not updated for 3.14 |
| Rate limiting FAIL in harness | No slowapi middleware | Out of scope for this sprint, but production blocker |

## What to Improve

1. **Complete BoxLite framework migration** — Add `get_framework_config()` import, use `file_extension` property
2. **Fix BoxLite test fixture** — Add testcontainers or mock sandbox for CI
3. **Add rate limiting middleware** — `slowapi` integration in `main.py`
4. **Update Python deps for 3.14** — Pin pydantic/anthropic to compatible versions
5. **Automate ADR generation** — Link retro findings to ADR creation

## Metrics

- **Files changed**: 45 (22 core + 23 planning/docs)
- **Tests**: 141 passing, 46 pre-existing blocked
- **Lines**: +2055/-237 net
- **Time**: ~3 hours across 7 phases
- **Patterns adopted from OSS**: 3 (Prompt-per-Stack, Spec-file IR, Parallel dispatch)