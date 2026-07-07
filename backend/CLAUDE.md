# Perfect Web Clone — Backend Development Rules

> **About this file:** TDD-first, strict TypeScript/Python, hexagonal architecture, security gates.
> Skills loaded on-demand. Agents verify compliance. Plans in `plans/`. Always on branch with PR.

## Core Philosophy

**TEST-DRIVEN DEVELOPMENT IS NON-NEGOTIABLE.** Every single line of production code must be written in response to a failing test. No exceptions.

**Development cycle:** RED → GREEN → MUTATE → KILL MUTANTS → REFACTOR. Then present work, await commit approval.

## Quick Reference

| Rule | Details |
|------|---------|
| Tests first | No production code without failing test |
| Types | Strict Python typing, no `Any` at boundaries |
| Immutability | `readonly`, `as const`, spread over mutation |
| Functions | Small, pure, single responsibility |
| Comments | None — code is self-documenting |
| Factory data | Test data from factory functions, not `let`/`beforeEach` |

## Workflow

1. **Plan** → `/plan` (creates `plans/<name>.md` on branch with PR)
2. **Build** → RED-GREEN-MUTATE-KILL MUTANTS-REFACTOR per step
3. **Commit** → Present work, await explicit approval
4. **Review** → `/pr` (quality gates: tests, typecheck, lint, mutation testing)
5. **Merge** → `/continue` (pull main, update plan, new branch)
6. **Complete** → Merge learnings (`learn`, `adr`), DELETE plan file

## CRITICAL Rules (Evolved 2026-07-07)

### Rule 1: Async-First Adapter Pattern
All external service adapters MUST use async clients:
- LLM: Use `AsyncAnthropic`, not `Anthropic`
- HTTP: Use `httpx.AsyncClient`, not `requests`
- DB: Use `asyncpg`/`aioredis`, not `psycopg`/`redis-py`

**Harness check:** `scripts/check-async-adapters.sh`
**Block ship if:** Sync client found in adapter files.

### Rule 2: LLM Response Validation
All LLM adapter responses MUST handle:
1. Empty content array: `if response.content and len(response.content) > 0`
2. Missing usage: `response.usage or default_usage`
3. None stop_reason: `response.stop_reason or "end_turn"`

**Block ship if:** Unguarded `response.content[0]` access found.

### Rule 3: Security Completeness
For each security function (`validate_path`, `check_command_allowed`, etc.):
1. List ALL code paths that should use it
2. Verify EACH path applies the check
3. Report missing applications as findings

**Harness check:** `scripts/check-security-completeness.sh`
**Block ship if:** File operation without security check found.

### Rule 4: Cache Contract TTL Enforcement
All cache implementations MUST:
1. `get()`: Return None if expired (lazy eviction)
2. `exists()`: Return False if expired (lazy eviction)
3. `set()`: Store with TTL
4. `delete()`: Remove entry

**Harness check:** `scripts/check-cache-ttl.sh`
**Block ship if:** Cache adapter exists() test missing TTL scenario.

### Rule 5: External Service Resilience
All adapters wrapping external services MUST:
1. Wrap operations in `try/except`
2. Log warnings on failure (not errors for expected failures)
3. Return safe defaults (`None`, `False`, `[]`, `0`)
4. Never raise on connection failures (graceful degradation)

## HIGH Rules

### Rule 6: Hexagonal Architecture
- Domain has zero external dependencies
- All boundaries use interfaces (Protocol classes)
- Dependencies point inward
- Ports in `ports/`, adapters in `adapters/`

### Rule 7: Security Gates
1. CORS: Environment-based (`CORS_ORIGINS` env var)
2. Rate limiting: Auth endpoints (slowapi 100/min read, 30/min write)
3. Path traversal: ALL file ops (validate_path)
4. Command injection: Shell allowlist (BLOCKED_COMMANDS, INJECTION_PATTERNS)
5. API key auth: Optional when `API_KEY` env set
6. Error format: Unified `{"success": false, "error": "message"}`

### Rule 8: Test Coverage
- All new features must have tests
- All bug fixes must have regression tests
- Factory functions for test data (not `let`/`beforeEach`)
- Mock external services in unit tests

## MEDIUM Rules

### Rule 9: Framework Agnostic
- All framework-specific constants in central config (`framework_config.py`)
- Import `get_framework_config()` everywhere
- No hardcoded `.jsx`/`.tsx` extensions

### Rule 10: Documentation
- Docstrings for all public methods
- ADRs for architectural decisions
- Patterns documented in `.vibe/learnings/patterns/`

## Tools

| Layer | Choice | License |
|-------|--------|---------|
| Cache/KV | Valkey (Redis-compatible) | BSD |
| SQL/State | PostgreSQL + pgvector | PostgreSQL |
| Agent Framework | CrewAI + Smolagents | MIT/Apache 2.0 |
| Sandbox | E2B (Firecracker) | Apache 2.0 |

## Architecture

Hexagonal (ports & adapters). Domain has zero external dependencies. All boundaries use interfaces. Dependencies point inward.

```
Driving Adapters ──► Use Cases ──► Driven Adapters
(REST/MCP/A2A)      (pure logic)   (Qdrant/Kuzu/Valkey/...)
```

## Harness Scripts

| Script | Purpose |
|--------|---------|
| `scripts/check-async-adapters.sh` | Block sync clients in adapters |
| `scripts/check-security-completeness.sh` | Verify security on all file ops |
| `scripts/check-cache-ttl.sh` | Verify cache TTL enforcement |

## Documentation Types

| Agent | Purpose | Output |
|-------|---------|--------|
| `progress-guardian` | Track work | `plans/*.md` (deleted when done) |
| `adr` | Why decisions | `docs/adr/*.md` (permanent) |
| `learn` | How to work | This file (updates) |
| `docs-guardian` | What it does | README, guides (permanent) |
