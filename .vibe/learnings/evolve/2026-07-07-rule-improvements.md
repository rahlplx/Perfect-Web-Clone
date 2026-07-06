# Evolve: Rule Improvements from Framework-Agnostic Hardening

## Proposed Rule Changes

### Rule 1: Mandatory OSS Mining Before Major Refactors
**Current**: No explicit rule
**Proposed**: Add to `/vibe:think` phase — "For any refactor affecting >10 files, mine 3+ OSS projects for patterns first"

**Rationale**: Found 3 mature patterns in 8 projects that saved ~2 weeks of design iteration.

### Rule 2: Baseline Regression Tests Before Touching Code
**Current**: TDD enforced but no explicit "baseline test" pattern
**Proposed**: Add to `tdd` skill — "Before refactoring, write `test_baseline_<feature>.py` locking current behavior"

**Rationale**: 9 baseline tests caught 0 regressions across 22 file changes.

### Rule 3: Framework Config as Single Source of Truth
**Current**: Ad-hoc constants scattered
**Proposed**: Add to `hexagonal-architecture` skill — "All framework-specific constants in central config; import everywhere"

**Rationale**: `framework_config.py` became the only file needing changes for new frameworks.

### Rule 4: Docstring Terminology Sweep Checklist
**Current**: No rule for terminology consistency
**Proposed**: Add to `refactor-scan` skill — "After framework refactor, grep for old terminology in comments/docstrings"

**Rationale**: Found 18+ "JSX/React" references in comments after code was already framework-agnostic.

### Rule 5: Parallel Subagent Dispatch for Independent Slices
**Current**: Sequential execution assumed
**Proposed**: Add to `vibe-break` skill — "If slices share <20% files, dispatch in parallel via worktrees"

**Rationale**: S02-S04 completed in 1 session vs 3 sequential.

### Rule 6: BoxLite Layer Requires Framework Config Import
**Current**: BoxLite uses `sandbox.framework` attribute only
**Proposed**: Add to `build-mcp-server` / agent skills — "Sandbox layer must import `get_framework_config()` for extensions"

**Rationale**: 2 MEDIUM findings from missing `file_extension` in boxlite.

### Rule 7: CI Gate for Pre-Existing Test Failures
**Current**: 46 pre-existing failures in `test_boxlite_tools.py` not tracked
**Proposed**: Add to `vibe-harness` — "Track flaky/blocked tests in `.vibe/known-failures.json` with owner/ETA"

**Rationale**: Prevents "tests pass" confusion when pre-existing failures exist.

### Rule 8: Rate Limiting as Ship Gate
**Current**: Harness check 4 (rate limiting) = FAIL but not blocking
**Proposed**: Add to `vibe-ship` — "Rate limiting on auth endpoints required for production PRs"

**Rationale**: OWASP Top 10 item, easy `slowapi` integration.

---

## Skill Updates Needed

| Skill | Update |
|-------|--------|
| `tdd` | Add baseline test pattern |
| `refactor-scan` | Add terminology sweep |
| `vibe-break` | Add parallel dispatch guidance |
| `vibe-harness` | Add known-failures tracking |
| `vibe-ship` | Add rate limiting gate |
| `hexagonal-architecture` | Add framework config SOT rule |
| `build-mcp-server` | Add sandbox framework config import |

---

## Auto-Improvement Loop

This retro → learn → evolve cycle should be automated:
1. After each `/vibe:auto` run, extract retro findings
2. Pattern-match against existing rules
3. Propose rule diffs
4. Human approves → merge to `.claude/CLAUDE.md` or skill files
5. Next run uses improved rules

**Telemetry to track**:
- Files changed per sprint
- Test count delta
- Retro findings by severity
- Rule proposals accepted/rejected
- Time per phase