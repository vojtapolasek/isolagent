#!/bin/bash
set -euo pipefail

RESULTS_FILE="/tmp/test-results.json"
PASSED=0
FAILED=0
DETAILS="[]"

check() {
    local name="$1"
    local result="$2"
    local detail="${3:-}"

    if [ "$result" = "pass" ]; then
        PASSED=$((PASSED + 1))
        DETAILS=$(echo "$DETAILS" | jq --arg n "$name" --arg s "pass" --arg d "$detail" \
            '. + [{"name": $n, "status": $s, "detail": $d}]')
    else
        FAILED=$((FAILED + 1))
        DETAILS=$(echo "$DETAILS" | jq --arg n "$name" --arg s "fail" --arg d "$detail" \
            '. + [{"name": $n, "status": $s, "detail": $d}]')
    fi
}

# Check environment variables
if [ "${SANDBOX_TEST_VAR:-}" = "expected-value" ]; then
    check "env_var_set" "pass"
else
    check "env_var_set" "fail" "SANDBOX_TEST_VAR='${SANDBOX_TEST_VAR:-<unset>}', expected 'expected-value'"
fi

if [ "${SANDBOX_TEST_EMPTY+set}" = "set" ] && [ -z "$SANDBOX_TEST_EMPTY" ]; then
    check "env_var_empty" "pass"
else
    check "env_var_empty" "fail" "SANDBOX_TEST_EMPTY not set or not empty"
fi

# Check project sync
if [ -d /isolagent/project ]; then
    check "project_dir_exists" "pass"
else
    check "project_dir_exists" "fail" "/isolagent/project does not exist"
fi

if [ -f /isolagent/project/README.md ]; then
    check "project_file_synced" "pass"
else
    check "project_file_synced" "fail" "/isolagent/project/README.md not found"
fi

# Check extra syncs
if [ -d /isolagent/extra-test ]; then
    check "extra_sync_dir_exists" "pass"
else
    check "extra_sync_dir_exists" "fail" "/isolagent/extra-test does not exist"
fi

if [ -f /isolagent/extra-test/extra-marker.txt ] && \
   grep -q "extra-sync-ok" /isolagent/extra-test/extra-marker.txt; then
    check "extra_sync_content" "pass"
else
    check "extra_sync_content" "fail" "/isolagent/extra-test/extra-marker.txt missing or wrong content"
fi

# Check guest files
if [ -f "$HOME/.test-marker" ] && grep -q "isolagent-test-ok" "$HOME/.test-marker"; then
    check "guest_file_marker" "pass"
else
    check "guest_file_marker" "fail" "~/.test-marker missing or wrong content"
fi

# Produce file modifications for output extraction testing
cd /isolagent/project
echo "modified by agent" >> README.md
git add -A
git commit --no-verify -m "agent: test modification"

check "file_modification" "pass"

# Write results
jq -n \
    --argjson passed "$PASSED" \
    --argjson failed "$FAILED" \
    --argjson details "$DETAILS" \
    '{"passed": $passed, "failed": $failed, "all_passed": ($failed == 0), "checks": $details}' \
    > "$RESULTS_FILE"

if [ "$FAILED" -gt 0 ]; then
    echo "FAILED: $FAILED checks failed" >&2
    cat "$RESULTS_FILE" >&2
    exit 1
fi

echo "ALL CHECKS PASSED ($PASSED/$PASSED)"
