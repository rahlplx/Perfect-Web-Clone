# Evolve: Security Hardening Session — Rule Proposals

## Session Context
- **Date**: 2026-07-07
- **Trigger**: /vibe:review found 5 issues (2 CRITICAL, 3 HIGH)
- **Tests**: 610/611 passing

---

## PROPOSED RULE CHANGES

### Rule 1: Async-First Adapter Pattern (NEW)
**Severity**: CRITICAL gap
**Proposed**: Add to `hexagonal-architecture` skill + `vibe-harness`

```
## Async Adapter Rule
All external service adapters MUST use async clients:
- LLM: Use AsyncAnthropic, not Anthropic
- HTTP: Use httpx AsyncClient, not requests
- DB: Use asyncpg/aioredis, not psycopg/redis-py

Harness check: Grep for sync client constructors in adapter files.
Block ship if sync client found in async adapter.
```

**Evidence**: AnthropicAdapter used `anthropic.Anthropic()` (sync) in async `complete()` method. This blocks the event loop and causes production deadlocks under load.

**Impact**: Prevents event loop blocking for all external integrations.

---

### Rule 2: LLM Response Validation Pattern (NEW)
**Severity**: CRITICAL gap
**Proposed**: Add to `agent-protocol` skill

```
## LLM Response Validation
All LLM adapter responses MUST handle:
1. Empty content array: `if response.content and len(response.content) > 0`
2. Missing usage: `response.usage or default_usage`
3. None stop_reason: `response.stop_reason or "end_turn"`

Harness check: Grep for `response.content[0]` without guard.
Block ship if unguarded content access found.
```

**Evidence**: `response.content[0].text` crashes with IndexError when Claude returns tool-use-only responses (empty content array).

**Impact**: Prevents crashes on valid Claude API responses.

---

### Rule 3: Complete Security Application Audit (IMPROVE)
**Severity**: HIGH gap (partial existing rule)
**Proposed**: Add to `vibe-harness` security gate

```
## Security Completeness Check
For each security function (validate_path, check_command_allowed, etc.):
1. List ALL code paths that should use it
2. Verify EACH path applies the check
3. Report missing applications as findings

Pattern: "validate_path" appears in write/read/delete/list but NOT in rename/create → INCOMPLETE

Harness check: 
  grep -rn "async def.*path" backend/ | grep -v validate_path → FAIL
```

**Evidence**: Path traversal protection applied to write_file, read_file, delete_file, list_files but missed rename_file and create_directory. Same vulnerability class, inconsistent application.

**Impact**: Ensures security functions are applied to ALL relevant code paths, not just the ones remembered.

---

### Rule 4: Cache Contract TTL Enforcement (NEW)
**Severity**: HIGH gap
**Proposed**: Add to `cache-port` contract + harness

```
## Cache Port Contract
All cache implementations MUST:
1. `get()`: Return None if expired (lazy eviction)
2. `exists()`: Return False if expired (lazy eviction)
3. `set()`: Store with TTL
4. `delete()`: Remove entry

Harness check: Cache adapter tests MUST include TTL expiry tests for ALL methods.
Block ship if exists() test missing TTL scenario.
```

**Evidence**: `InMemoryCacheAdapter.exists()` returned `True` for expired entries because it only checked `key in self._store` without TTL validation.

**Impact**: Prevents stale data reads from cache.

---

### Rule 5: External Service Resilience Pattern (NEW)
**Severity**: HIGH gap
**Proposed**: Add to `hexagonal-architecture` skill

```
## External Service Resilience
All adapters wrapping external services MUST:
1. Wrap operations in try/except
2. Log warnings on failure (not errors for expected failures)
3. Return safe defaults (None, False, [], 0)
4. Never raise on connection failures (graceful degradation)

Harness check: Grep for adapter methods without try/except.
Flag methods that call external services without error handling.
```

**Evidence**: `RedisCacheAdapter` had zero error handling. Any Redis connection failure would crash the entire application instead of degrading gracefully.

**Impact**: Prevents cascading failures when external services are unavailable.

---

## IMPROVED RULES

### Rule 6: Security Harness Gate Enhancement (IMPROVE)
**Current**: Basic CORS check
**Proposed**: Expand to full OWASP checklist

```
## Security Gate (Enhanced)
1. CORS: Environment-based ✓ (existing)
2. Rate limiting: Auth endpoints ✓ (existing)
3. Path traversal: ALL file ops ✓ (NEW - enforce completeness)
4. Command injection: Shell allowlist ✓ (existing)
5. API key auth: Optional when env set ✓ (existing)
6. Error format: Unified response ✓ (existing)
```

---

## SKILL UPDATES NEEDED

| Skill | Update | Priority |
|-------|--------|----------|
| `hexagonal-architecture` | Add async-first adapter rule | CRITICAL |
| `agent-protocol` | Add LLM response validation | CRITICAL |
| `vibe-harness` | Add security completeness check | HIGH |
| `vibe-harness` | Add cache TTL enforcement | HIGH |
| `cache-port` | Document TTL contract | HIGH |
| `hexagonal-architecture` | Add resilience pattern | HIGH |

---

## AUTO-EVOLUTION TRIGGERS MET

- ✅ After `/vibe:review` — Found 5 issues
- ✅ CRITICAL quality gap — Sync client in production code
- ✅ Pattern across multiple areas — Security inconsistency (2 missed paths)

---

## PROPOSED HARNESS SCRIPTS

### scripts/check-async-adapters.sh
```bash
#!/bin/bash
# Check for sync client constructors in adapter files
SYNC_PATTERNS="anthropic\.Anthropic\(|requests\.|redis\.Redis\(|psycopg2?"
ADAPTER_DIR="backend/adapters"

if grep -rn "$SYNC_PATTERNS" "$ADAPTER_DIR" --include="*.py"; then
  echo "FAIL: Sync client found in adapter. Use async variant."
  exit 1
fi
echo "PASS: All adapters use async clients"
```

### scripts/check-security-completeness.sh
```bash
#!/bin/bash
# Check that validate_path is applied to ALL file operations
SECURITY_FUNCS="validate_path|check_command_allowed"
FILE_OPS="async def (write_file|read_file|delete_file|list_files|rename_file|create_directory)"

MISSING=$(grep -rn "$FILE_OPS" backend/ --include="*.py" | grep -v "$SECURITY_FUNCS" | wc -l)

if [ "$MISSING" -gt 0 ]; then
  echo "FAIL: $MISSING file operations missing security checks"
  exit 1
fi
echo "PASS: All file operations have security checks"
```

### scripts/check-cache-ttl.sh
```bash
#!/bin/bash
# Check that cache exists() has TTL handling
CACHE_ADAPTERS="backend/adapters/cache/*.py"

for file in $CACHE_ADAPTERS; do
  if grep -q "async def exists" "$file" && ! grep -q "expires_at\|ttl\|time()" "$file"; then
    echo "FAIL: $file exists() missing TTL check"
    exit 1
  fi
done
echo "PASS: All cache adapters check TTL in exists()"
```

---

## Summary

| Change Type | Count | Severity |
|-------------|-------|----------|
| NEW rules | 5 | 2 CRITICAL, 3 HIGH |
| IMPROVED rules | 1 | HIGH |
| Skill updates | 6 | — |
| Harness scripts | 3 | — |
