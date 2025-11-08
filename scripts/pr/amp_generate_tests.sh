#!/bin/bash
# scripts/pr/amp_generate_tests.sh - Generate pytest tests using Amp CLI
#
# Usage: bash scripts/pr/amp_generate_tests.sh <PR_NUMBER>
# Example: bash scripts/pr/amp_generate_tests.sh 215

set -e

PR_NUMBER=$1

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed"
    exit 1
fi

echo "=== Amp CLI Test Generation for PR #$PR_NUMBER ==="
echo ""

# Ensure Amp directories exist
mkdir -p .claude/amp/prompts/pending
mkdir -p .claude/amp/responses/ready
mkdir -p /tmp/amp_tests

# Get changed Python files (excluding tests)
echo "Fetching changed files from PR #$PR_NUMBER..."
changed_files=$(gh pr diff $PR_NUMBER --name-only | grep '\.py$' | grep -v '^tests/' || echo "")

if [ -z "$changed_files" ]; then
    echo "No Python files changed (excluding tests)."
    exit 0
fi

echo "Changed Python files (non-test):"
echo "$changed_files"
echo ""

# Track UUIDs for all test generation tasks
test_uuids=()

for file in $changed_files; do
    if [ ! -f "$file" ]; then
        echo "Skipping $file (not found in working directory)"
        continue
    fi

    echo "Creating test generation prompt for: $file"

    # Generate UUID for this file's test generation
    test_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
    test_uuids+=("$test_uuid")

    # Determine if test file already exists
    base_name=$(basename "$file" .py)
    test_file="tests/test_${base_name}.py"

    if [ -f "$test_file" ]; then
        existing_tests=$(cat "$test_file")
        prompt_mode="append"
        prompt_text="Existing test file exists. Analyze the existing tests and new/changed code to suggest ADDITIONAL pytest test cases. Only output new test functions to append to the existing file.\n\nExisting tests:\n${existing_tests}\n\nNew/changed code:\n$(cat "$file")\n\nProvide only new test functions (complete pytest syntax) that cover new functionality not already tested."
    else
        prompt_mode="create"
        prompt_text="Generate comprehensive pytest tests for this Python module. Include: 1) Happy path tests, 2) Edge cases, 3) Error handling, 4) Async test cases if applicable. Output complete pytest test file.\n\nModule code:\n$(cat "$file")\n\nProvide complete test file content with imports, fixtures, and test functions."
    fi

    # Create test generation prompt
    cat > .claude/amp/prompts/pending/tests-${test_uuid}.json << EOF
{
  "id": "${test_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "${prompt_text}",
  "context": {
    "project": "mcp-memory-service",
    "task": "test-generation",
    "pr_number": "${PR_NUMBER}",
    "source_file": "${file}",
    "test_file": "${test_file}",
    "mode": "${prompt_mode}"
  },
  "options": {
    "timeout": 180000,
    "format": "python"
  }
}
EOF

    echo "  ✅ Created prompt for ${file} (${prompt_mode} mode)"
done

echo ""
echo "=== Created ${#test_uuids[@]} test generation prompts ==="
echo ""

# Show Amp commands to run
echo "=== Run these Amp commands (can run in parallel) ==="
for uuid in "${test_uuids[@]}"; do
    echo "amp @.claude/amp/prompts/pending/tests-${uuid}.json &"
done
echo ""

echo "=== Or use this one-liner to run all in background ==="
parallel_cmd=""
for uuid in "${test_uuids[@]}"; do
    parallel_cmd+="(amp @.claude/amp/prompts/pending/tests-${uuid}.json > /tmp/amp-test-${uuid}.log 2>&1 &); "
done
parallel_cmd+="sleep 10 && bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids '$(IFS=,; echo "${test_uuids[*]}")'"
echo "$parallel_cmd"
echo ""

# Save UUIDs for later collection
echo "$(IFS=,; echo "${test_uuids[*]}")" > /tmp/amp_test_generation_uuids_${PR_NUMBER}.txt
echo "UUIDs saved to /tmp/amp_test_generation_uuids_${PR_NUMBER}.txt"
echo ""

echo "After Amp completes, tests will be in .claude/amp/responses/consumed/"
echo "Extract test content and review before committing to tests/ directory"
