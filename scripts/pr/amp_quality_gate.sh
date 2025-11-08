#!/bin/bash
# scripts/pr/amp_quality_gate.sh - Parallel quality checks using Amp CLI
#
# Usage: bash scripts/pr/amp_quality_gate.sh <PR_NUMBER>
# Example: bash scripts/pr/amp_quality_gate.sh 215
# For local branch (pre-PR): bash scripts/pr/amp_quality_gate.sh 0

set -e

PR_NUMBER=$1

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>"
    echo "Use 0 for local branch (pre-PR checks)"
    exit 1
fi

# Ensure Amp prompt directories exist
mkdir -p .claude/amp/prompts/pending
mkdir -p .claude/amp/responses/ready

echo "=== Amp CLI Quality Gate for PR #$PR_NUMBER ==="
echo ""

# Get changed Python files
if [ "$PR_NUMBER" = "0" ]; then
    echo "Analyzing local branch changes..."
    changed_files=$(git diff --name-only origin/main | grep '\.py$' || echo "")
else
    if ! command -v gh &> /dev/null; then
        echo "Error: GitHub CLI (gh) is not installed"
        exit 1
    fi
    echo "Fetching changed files from PR #$PR_NUMBER..."
    changed_files=$(gh pr diff $PR_NUMBER --name-only | grep '\.py$' || echo "")
fi

if [ -z "$changed_files" ]; then
    echo "No Python files changed."
    exit 0
fi

echo "Changed Python files:"
echo "$changed_files"
echo ""

# Generate UUIDs for each check
complexity_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
security_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)
typehints_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)

# Store UUIDs for result collection
echo "$complexity_uuid,$security_uuid,$typehints_uuid" > /tmp/amp_quality_gate_uuids_${PR_NUMBER}.txt

echo "Creating Amp prompts for parallel processing..."
echo ""

# Create complexity check prompt
cat > .claude/amp/prompts/pending/complexity-${complexity_uuid}.json << EOF
{
  "id": "${complexity_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "Analyze code complexity for each function in these files. Rating scale: 1-10 (1=simple, 10=very complex). ONLY report functions with score >7 in this exact format: 'File:Function: Score X - Reason'. If all functions score ≤7, respond: 'COMPLEXITY_OK'. Files:\n\n$(echo "$changed_files" | while read file; do echo "=== $file ==="; cat "$file" 2>/dev/null || echo "File not found"; echo ""; done)",
  "context": {
    "project": "mcp-memory-service",
    "task": "complexity-analysis",
    "pr_number": "${PR_NUMBER}"
  },
  "options": {
    "timeout": 120000,
    "format": "text"
  }
}
EOF

# Create security scan prompt
cat > .claude/amp/prompts/pending/security-${security_uuid}.json << EOF
{
  "id": "${security_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "Security audit for vulnerabilities: SQL injection (raw SQL, string formatting in queries), XSS (unescaped HTML output), command injection (os.system, subprocess with shell=True), path traversal (user input in file paths), hardcoded secrets (API keys, passwords). IMPORTANT: Output format - If ANY vulnerability found: 'VULNERABILITY_DETECTED: [type] - [details]'. If NO vulnerabilities: 'SECURITY_CLEAN'. Files:\n\n$(echo "$changed_files" | while read file; do echo "=== $file ==="; cat "$file" 2>/dev/null || echo "File not found"; echo ""; done)",
  "context": {
    "project": "mcp-memory-service",
    "task": "security-scan",
    "pr_number": "${PR_NUMBER}"
  },
  "options": {
    "timeout": 120000,
    "format": "text"
  }
}
EOF

# Create type hints check prompt
cat > .claude/amp/prompts/pending/typehints-${typehints_uuid}.json << EOF
{
  "id": "${typehints_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "Check type hint coverage for these Python files. Report: 1) Total functions/methods, 2) Functions with complete type hints, 3) Functions missing type hints (list names), 4) Coverage percentage. Output format: 'COVERAGE: X%' then 'MISSING: function1, function2, ...' (or 'NONE' if all covered). Files:\n\n$(echo "$changed_files" | while read file; do echo "=== $file ==="; cat "$file" 2>/dev/null || echo "File not found"; echo ""; done)",
  "context": {
    "project": "mcp-memory-service",
    "task": "type-hints",
    "pr_number": "${PR_NUMBER}"
  },
  "options": {
    "timeout": 120000,
    "format": "text"
  }
}
EOF

echo "✅ Created 3 Amp prompts for parallel processing"
echo ""
echo "=== Run these Amp commands in parallel (in separate terminals or background) ==="
echo ""
echo "amp @.claude/amp/prompts/pending/complexity-${complexity_uuid}.json &"
echo "amp @.claude/amp/prompts/pending/security-${security_uuid}.json &"
echo "amp @.claude/amp/prompts/pending/typehints-${typehints_uuid}.json &"
echo ""
echo "=== Then collect results with ==="
echo "bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids '${complexity_uuid},${security_uuid},${typehints_uuid}'"
echo ""
echo "=== Or use this one-liner to run all in background ==="
echo "(amp @.claude/amp/prompts/pending/complexity-${complexity_uuid}.json > /tmp/amp-complexity.log 2>&1 &); (amp @.claude/amp/prompts/pending/security-${security_uuid}.json > /tmp/amp-security.log 2>&1 &); (amp @.claude/amp/prompts/pending/typehints-${typehints_uuid}.json > /tmp/amp-typehints.log 2>&1 &); sleep 10 && bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids '${complexity_uuid},${security_uuid},${typehints_uuid}'"
