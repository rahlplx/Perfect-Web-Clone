# Plan: Hardening Follow-up Fixes

## Issues to Fix

### 1. MEDIUM: BoxLite Framework-Agnostic Migration (2 findings)
- **File**: `backend/boxlite/boxlite_mcp_executor.py`
- **Line 1493**: `target_files` hardcodes `.jsx` extension
- **Line 1842**: `component_path` hardcodes `.jsx` extension
- **Fix**: Import `get_framework_config()` and use `config.file_extension`

### 2. FAIL: Rate Limiting (Harness Check 4)
- **File**: `backend/main.py`
- **Fix**: Add `slowapi` middleware with rate limits on auth/websocket endpoints

### 3. BLOCKED: 46 BoxLite Tests
- **File**: `backend/tests/test_boxlite_tools.py`
- **Issue**: Missing BoxLite sandbox fixture
- **Fix**: Add testcontainers-based fixture or mock sandbox

### 4. LSP Errors (Python 3.14 Typing)
Multiple files with typing issues due to Python 3.14 + anthropic SDK incompatibilities:
- `boxlite/worker_agent.py` - ModuleSpec/loader issues
- `agent/worker_agent.py` - Same + MessageParam typing
- `agent/task_contract.py` - None assignable issues
- `agent/mcp_tools.py` - Import resolution + worker_id typing
- `boxlite/boxlite_mcp_executor.py` - TypeIs + CommandResult

## Priority Order
1. BoxLite framework migration (MEDIUM, core functionality)
2. Rate limiting (FAIL, production blocker)
3. LSP typing fixes (code quality)
4. Test fixture (unblocks 46 tests)

## Success Criteria
- [ ] 0 MEDIUM findings in review
- [ ] Harness: 6/6 PASS
- [ ] 141+46 = 187 tests passing
- [ ] 0 LSP errors (or only external dep issues)