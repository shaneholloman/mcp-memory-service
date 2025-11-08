#!/bin/bash
# scripts/pr/amp_collect_results.sh - Collect Amp analysis results
#
# Usage: bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids "uuid1,uuid2,uuid3"
# Example: bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids "$(cat /tmp/amp_quality_gate_uuids_215.txt)"

set -e

# Default values
TIMEOUT=300
UUIDS=""
POLL_INTERVAL=5

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --uuids)
            UUIDS="$2"
            shift 2
            ;;
        --poll-interval)
            POLL_INTERVAL="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 --timeout SECONDS --uuids 'uuid1,uuid2,uuid3' [--poll-interval SECONDS]"
            exit 1
            ;;
    esac
done

if [ -z "$UUIDS" ]; then
    echo "Error: --uuids required"
    echo "Usage: $0 --timeout SECONDS --uuids 'uuid1,uuid2,uuid3'"
    exit 1
fi

echo "=== Collecting Amp Results ==="
echo "Timeout: ${TIMEOUT}s"
echo "Poll Interval: ${POLL_INTERVAL}s"
echo "UUIDs: $UUIDS"
echo ""

# Split UUIDs into array
IFS=',' read -ra UUID_ARRAY <<< "$UUIDS"
TOTAL_TASKS=${#UUID_ARRAY[@]}

echo "Waiting for $TOTAL_TASKS Amp tasks to complete..."
echo ""

# Track completion
COMPLETED=0
ELAPSED=0
START_TIME=$(date +%s)

# Results storage
declare -A RESULTS

while [ $ELAPSED -lt $TIMEOUT ] && [ $COMPLETED -lt $TOTAL_TASKS ]; do
    for uuid in "${UUID_ARRAY[@]}"; do
        # Skip if already collected
        if [ -n "${RESULTS[$uuid]}" ]; then
            continue
        fi

        # Check for response file
        response_file=".claude/amp/responses/ready/${uuid}.json"
        if [ -f "$response_file" ]; then
            echo "✅ Collected result for task: ${uuid}"
            RESULTS[$uuid]=$(cat "$response_file")
            COMPLETED=$((COMPLETED + 1))

            # Move to consumed
            mkdir -p .claude/amp/responses/consumed
            mv "$response_file" ".claude/amp/responses/consumed/${uuid}.json"
        fi
    done

    # Update elapsed time
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))

    # Progress update
    if [ $COMPLETED -lt $TOTAL_TASKS ]; then
        echo "Progress: $COMPLETED/$TOTAL_TASKS tasks completed (${ELAPSED}s elapsed)"
        sleep $POLL_INTERVAL
    fi
done

echo ""
echo "=== Collection Complete ==="
echo "Completed: $COMPLETED/$TOTAL_TASKS tasks"
echo "Elapsed: ${ELAPSED}s"
echo ""

# Analyze results
if [ $COMPLETED -eq 0 ]; then
    echo "❌ No results collected (timeout or Amp tasks not run)"
    exit 1
fi

# Parse and aggregate results
echo "=== Quality Gate Results ==="
echo ""

COMPLEXITY_OK=true
SECURITY_OK=true
TYPEHINTS_OK=true
EXIT_CODE=0

for uuid in "${!RESULTS[@]}"; do
    result_json="${RESULTS[$uuid]}"

    # Extract output using jq (if available) or grep
    if command -v jq &> /dev/null; then
        output=$(echo "$result_json" | jq -r '.output // .response // ""')
    else
        output=$(echo "$result_json" | grep -oP '"output"\s*:\s*"\K[^"]+' || echo "$result_json")
    fi

    # Determine task type from response file context
    if echo "$output" | grep -q "COMPLEXITY"; then
        echo "--- Complexity Analysis ---"
        if echo "$output" | grep -q "COMPLEXITY_OK"; then
            echo "✅ All functions have complexity ≤7"
        else
            echo "⚠️  High complexity functions detected:"
            echo "$output" | grep -v "COMPLEXITY_OK"
            COMPLEXITY_OK=false
            EXIT_CODE=1
        fi
        echo ""
    elif echo "$output" | grep -q "SECURITY"; then
        echo "--- Security Scan ---"
        if echo "$output" | grep -q "SECURITY_CLEAN"; then
            echo "✅ No security vulnerabilities detected"
        else
            echo "🔴 SECURITY VULNERABILITIES DETECTED:"
            echo "$output"
            SECURITY_OK=false
            EXIT_CODE=2  # Critical
        fi
        echo ""
    elif echo "$output" | grep -q "COVERAGE"; then
        echo "--- Type Hints Coverage ---"
        coverage=$(echo "$output" | grep -oP 'COVERAGE:\s*\K\d+' || echo "0")
        echo "Coverage: ${coverage}%"

        if [ "$coverage" -ge 80 ]; then
            echo "✅ Type hints coverage is adequate (≥80%)"
        else
            echo "⚠️  Type hints coverage below 80%"
            missing=$(echo "$output" | grep -oP 'MISSING:\s*\K.*' || echo "")
            if [ "$missing" != "NONE" ] && [ -n "$missing" ]; then
                echo "Missing type hints: $missing"
            fi
            TYPEHINTS_OK=false
            if [ $EXIT_CODE -eq 0 ]; then
                EXIT_CODE=1
            fi
        fi
        echo ""
    else
        # Generic output
        echo "--- Result (${uuid}) ---"
        echo "$output"
        echo ""
    fi
done

# Summary
echo "=== Summary ==="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ ALL QUALITY CHECKS PASSED"
    echo "- Complexity: ✅ OK"
    echo "- Security: ✅ OK"
    echo "- Type Hints: ✅ OK"
elif [ $EXIT_CODE -eq 2 ]; then
    echo "🔴 CRITICAL FAILURE: Security vulnerabilities detected"
    echo "- Complexity: $([ "$COMPLEXITY_OK" = true ] && echo "✅ OK" || echo "⚠️  Issues")"
    echo "- Security: 🔴 VULNERABILITIES"
    echo "- Type Hints: $([ "$TYPEHINTS_OK" = true ] && echo "✅ OK" || echo "⚠️  Issues")"
else
    echo "⚠️  QUALITY GATE WARNINGS"
    echo "- Complexity: $([ "$COMPLEXITY_OK" = true ] && echo "✅ OK" || echo "⚠️  Issues")"
    echo "- Security: $([ "$SECURITY_OK" = true ] && echo "✅ OK" || echo "🔴 Issues")"
    echo "- Type Hints: $([ "$TYPEHINTS_OK" = true ] && echo "✅ OK" || echo "⚠️  Issues")"
fi
echo ""

# Save aggregated results to JSON
cat > /tmp/amp_quality_results.json << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "total_tasks": $TOTAL_TASKS,
  "completed_tasks": $COMPLETED,
  "elapsed_seconds": $ELAPSED,
  "summary": {
    "complexity_ok": $COMPLEXITY_OK,
    "security_ok": $SECURITY_OK,
    "typehints_ok": $TYPEHINTS_OK,
    "exit_code": $EXIT_CODE
  },
  "details": $(for uuid in "${!RESULTS[@]}"; do echo "${RESULTS[$uuid]}"; done | jq -s '.')
}
EOF

echo "📊 Detailed results saved to /tmp/amp_quality_results.json"

exit $EXIT_CODE
