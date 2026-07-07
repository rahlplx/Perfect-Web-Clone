#!/bin/bash
# Harness: Check that validate_path is applied to ALL file operations
# Blocks ship if any file operation bypasses security checks

BACKEND_DIR="backend"
SECURITY_FUNCS="validate_path|check_command_allowed"
FILE_OPS="async def (write_file|read_file|delete_file|list_files|rename_file|create_directory)"

echo "Checking security completeness in $BACKEND_DIR..."

# Find file operations without security checks
MISSING=$(grep -rn "$FILE_OPS" "$BACKEND_DIR" --include="*.py" | grep -v "$SECURITY_FUNCS" | grep -v "test_" | grep -v "mock_" | wc -l)

if [ "$MISSING" -gt 0 ]; then
  echo "FAIL: $MISSING file operations missing security checks:"
  grep -rn "$FILE_OPS" "$BACKEND_DIR" --include="*.py" | grep -v "$SECURITY_FUNCS" | grep -v "test_" | grep -v "mock_"
  exit 1
fi

echo "PASS: All file operations have security checks"
exit 0
