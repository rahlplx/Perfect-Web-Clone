#!/bin/bash
# Harness: Check that cache exists() has TTL handling
# Blocks ship if cache adapter exists() method ignores expiration

CACHE_DIR="backend/adapters/cache"

echo "Checking cache TTL enforcement in $CACHE_DIR..."

for file in "$CACHE_DIR"/*.py; do
  if [ -f "$file" ]; then
    if grep -q "async def exists" "$file"; then
      if ! grep -q "expires_at\|ttl\|time()" "$file"; then
        echo "FAIL: $file exists() missing TTL check"
        exit 1
      fi
    fi
  fi
done

echo "PASS: All cache adapters check TTL in exists()"
exit 0
