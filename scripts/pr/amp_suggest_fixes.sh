#!/bin/bash
# scripts/pr/amp_suggest_fixes.sh - Generate fix suggestions using Amp CLI
#
# Usage: bash scripts/pr/amp_suggest_fixes.sh <PR_NUMBER>
# Example: bash scripts/pr/amp_suggest_fixes.sh 215

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

echo "=== Amp CLI Fix Suggestions for PR #$PR_NUMBER ==="
echo ""

# Ensure Amp directories exist
mkdir -p .claude/amp/prompts/pending
mkdir -p .claude/amp/responses/ready

# Get repository
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "doobidoo/mcp-memory-service")

# Fetch review comments
echo "Fetching review comments from PR #$PR_NUMBER..."
review_comments=$(gh api "repos/$REPO/pulls/$PR_NUMBER/comments" | \
    jq -r '[.[] | select(.user.login | test("bot|gemini|claude"))] | .[] | "- \(.path):\(.line) - \(.body[0:200])"' | \
    head -50)

if [ -z "$review_comments" ]; then
    echo "No review comments found."
    exit 0
fi

echo "Review Comments:"
echo "$review_comments"
echo ""

# Get PR diff
echo "Fetching PR diff..."
pr_diff=$(gh pr diff $PR_NUMBER | head -500)  # Limit to 500 lines to avoid token overflow

# Generate UUID for fix suggestions task
fixes_uuid=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid)

echo "Creating Amp prompt for fix suggestions..."

# Create fix suggestions prompt
cat > .claude/amp/prompts/pending/fixes-${fixes_uuid}.json << EOF
{
  "id": "${fixes_uuid}",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")",
  "prompt": "Analyze these code review comments and suggest specific fixes. DO NOT auto-apply changes. Output format: For each issue, provide: 1) File path, 2) Issue description, 3) Suggested fix (code snippet or explanation), 4) Rationale. Focus on safe, non-breaking changes (formatting, type hints, error handling, variable naming, import organization).\n\nReview comments:\n${review_comments}\n\nPR diff (current code):\n${pr_diff}\n\nProvide actionable fix suggestions in markdown format.",
  "context": {
    "project": "mcp-memory-service",
    "task": "fix-suggestions",
    "pr_number": "${PR_NUMBER}"
  },
  "options": {
    "timeout": 180000,
    "format": "markdown"
  }
}
EOF

echo "✅ Created Amp prompt for fix suggestions"
echo ""
echo "=== Run this Amp command ==="
echo "amp @.claude/amp/prompts/pending/fixes-${fixes_uuid}.json"
echo ""
echo "=== Then collect the suggestions ==="
echo "bash scripts/pr/amp_collect_results.sh --timeout 180 --uuids '${fixes_uuid}'"
echo ""

# Save UUID for later collection
echo "${fixes_uuid}" > /tmp/amp_fix_suggestions_uuid_${PR_NUMBER}.txt

echo "UUID saved to /tmp/amp_fix_suggestions_uuid_${PR_NUMBER}.txt for result collection"
