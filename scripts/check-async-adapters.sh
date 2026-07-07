#!/bin/bash
# Harness: Check for sync client constructors in adapter files
# Blocks ship if sync client found in async adapter context

ADAPTER_DIR="backend/adapters"
SYNC_PATTERNS="anthropic\.Anthropic\(\)|requests\.|redis\.Redis\(\)|psycopg2?"

echo "Checking for sync clients in $ADAPTER_DIR..."

if grep -rn "$SYNC_PATTERNS" "$ADAPTER_DIR" --include="*.py" 2>/dev/null; then
  echo "FAIL: Sync client found in adapter. Use async variant (AsyncAnthropic, httpx.AsyncClient, redis.asyncio)."
  exit 1
fi

echo "PASS: All adapters use async clients"
exit 0
