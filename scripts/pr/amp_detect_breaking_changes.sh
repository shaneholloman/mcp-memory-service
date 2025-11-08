#!/bin/bash
# scripts/pr/amp_detect_breaking_changes.sh - Detect breaking API changes using Amp CLI
#
# Usage: bash scripts/pr/amp_detect_breaking_changes.sh <BASE_BRANCH> <HEAD_BRANCH>
# Example: bash scripts/pr/amp_detect_breaking_changes.sh main feature/new-api

set -e

BASE_BRANCH=${1:-main}
HEAD_BRANCH=${2:-$(git branch --show-current)}

echo "=== Amp CLI Breaking Change Detection ==="
echo "Base Branch: $BASE_BRANCH"
echo "Head Branch: $HEAD_BRANCH"
echo ""

# Ensure Amp directories exist
mkdir -p .claude/amp/prompts/pending
mkdir -p .claude/amp/responses/ready

# Get API-related file changes
echo "Analyzing API changes..."
api_changes=$(git diff origin/$BASE_BRANCH...origin/$HEAD_BRANCH -- \
    src/mcp_memory_service/tools.py \
    src/mcp_memory_service/web/api/ \
    2>/dev/null || echo "")

if [ -z "$api_changes" ]; then
    echo "✅ No API changes detected"
    exit 0
fi

echo "API changes detected ($(echo "$api_changes" | wc -l) lines)"
echo ""

# Generate UUID for breaking change analysis
breaking_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)

echo "Creating Amp prompt for breaking change analysis..."

# Truncate large diffs to avoid token overflow
api_changes_truncated=$(echo "$api_changes" | head -300)

# Create breaking change analysis prompt
cat > .claude/amp/prompts/pending/breaking-${breaking_uuid}.json << EOF
{
  "id": "${breaking_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "Analyze these API changes for breaking changes. A breaking change is:\n- Removed function/method/endpoint\n- Changed function signature (parameters removed/reordered)\n- Changed return type in incompatible way\n- Renamed public API\n- Changed HTTP endpoint path/method\n- Changed MCP tool schema (added required parameters, removed optional parameters, changed parameter types)\n\nReport ONLY breaking changes with severity (CRITICAL/HIGH/MEDIUM). If no breaking changes, respond: 'BREAKING_CHANGES_NONE'.\n\nOutput format:\nSeverity: [CRITICAL|HIGH|MEDIUM]\nType: [removal|signature-change|rename|schema-change]\nLocation: [file:function/endpoint]\nDetails: [explanation]\nMigration: [suggested migration path]\n\nAPI Changes:\n${api_changes_truncated}",
  "context": {
    "project": "mcp-memory-service",
    "task": "breaking-change-detection",
    "base_branch": "${BASE_BRANCH}",
    "head_branch": "${HEAD_BRANCH}"
  },
  "options": {
    "timeout": 120000,
    "format": "text"
  }
}
EOF

echo "✅ Created Amp prompt for breaking change analysis"
echo ""
echo "=== Run this Amp command ==="
echo "amp @.claude/amp/prompts/pending/breaking-${breaking_uuid}.json"
echo ""
echo "=== Then collect the analysis ==="
echo "bash scripts/pr/amp_collect_results.sh --timeout 120 --uuids '${breaking_uuid}'"
echo ""

# Alternative: Direct analysis with custom result handler
echo "=== Or use this one-liner for immediate analysis ==="
echo "(amp @.claude/amp/prompts/pending/breaking-${breaking_uuid}.json > /tmp/amp-breaking.log 2>&1); sleep 5 && bash scripts/pr/amp_analyze_breaking_changes.sh '${breaking_uuid}'"
echo ""

# Save UUID for later collection
echo "${breaking_uuid}" > /tmp/amp_breaking_changes_uuid.txt
echo "UUID saved to /tmp/amp_breaking_changes_uuid.txt"
