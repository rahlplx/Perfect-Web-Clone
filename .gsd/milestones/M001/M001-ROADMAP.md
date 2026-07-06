# M001: Zero React Hardcodes — Full Framework Agnostic Hardening

## Risk
Medium — most changes are backend-only, test-covered, and the codebase is already 141/141 passing

## Dependencies
None

## Slices

### S01: Reverse Engineering & Audit
Mine OSS projects for patterns. Full backend audit for React/JSX references.
Risk: Low (research only)

### S02: worker_agent.py Framework-Aware Refactor
The highest-risk change. Make the fallback system prompt framework-aware.
Risk: High (core agent logic)

### S03: MCP Tools & Task Contract Sweep
Fix hardcoded .jsx extensions, docstrings, and any remaining React assumptions.
Risk: Low (well-understood changes)

### S04: BoxLite Worker Agent Sync
Audit and fix boxlite worker_agent.py parallel to main worker_agent.
Risk: Medium

### S05: Test Expansion & Harness
Add tests for all new code paths. Run production readiness harness.
Risk: Low
