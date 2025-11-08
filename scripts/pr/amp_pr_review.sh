#!/bin/bash
# scripts/pr/amp_pr_review.sh - Complete PR review workflow using Amp CLI
#
# Usage: bash scripts/pr/amp_pr_review.sh <PR_NUMBER>
# Example: bash scripts/pr/amp_pr_review.sh 215

set -e

PR_NUMBER=$1

if [ -z "$PR_NUMBER" ]; then
    echo "Usage: $0 <PR_NUMBER>"
    exit 1
fi

echo "=================================================================="
echo "        Amp CLI Complete PR Review Workflow"
echo "        PR #${PR_NUMBER}"
echo "=================================================================="
echo ""

START_TIME=$(date +%s)
WORKFLOW_EXIT_CODE=0

# Step 1: Quality Gate Checks
echo "=== Step 1: Quality Gate Checks (Parallel) ==="
echo "Running complexity, security, and type hint analysis..."
echo ""

bash scripts/pr/amp_quality_gate.sh $PR_NUMBER

# Prompt user to run Amp tasks
echo ""
echo "⚠️  MANUAL STEP REQUIRED: Run the Amp commands shown above"
echo ""
read -p "Press ENTER after running all Amp quality gate commands... " -r
echo ""

# Collect quality gate results
quality_uuids=$(cat /tmp/amp_quality_gate_uuids_${PR_NUMBER}.txt 2>/dev/null || echo "")
if [ -n "$quality_uuids" ]; then
    bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids "$quality_uuids"
    QUALITY_EXIT=$?

    if [ $QUALITY_EXIT -eq 2 ]; then
        echo ""
        echo "🔴 CRITICAL: Security vulnerabilities detected. Stopping workflow."
        echo "Fix security issues before continuing."
        exit 2
    elif [ $QUALITY_EXIT -eq 1 ]; then
        echo ""
        echo "⚠️  Quality gate warnings detected (non-blocking). Continuing..."
        WORKFLOW_EXIT_CODE=1
    fi
else
    echo "⚠️  Could not find quality gate UUIDs. Skipping collection."
fi

echo ""
echo "✅ Step 1 Complete: Quality Gate"
echo ""

# Step 2: Test Generation
echo "=== Step 2: Test Generation ==="
echo "Generating pytest tests for changed files..."
echo ""

bash scripts/pr/amp_generate_tests.sh $PR_NUMBER

echo ""
echo "⚠️  MANUAL STEP REQUIRED: Run the Amp test generation commands shown above"
echo ""
read -p "Press ENTER after running Amp test generation commands... " -r
echo ""

# Collect test generation results
test_uuids=$(cat /tmp/amp_test_generation_uuids_${PR_NUMBER}.txt 2>/dev/null || echo "")
if [ -n "$test_uuids" ]; then
    bash scripts/pr/amp_collect_results.sh --timeout 300 --uuids "$test_uuids"
    echo ""
    echo "✅ Tests generated. Review in .claude/amp/responses/consumed/"
else
    echo "⚠️  Could not find test generation UUIDs. Skipping collection."
fi

echo ""
echo "✅ Step 2 Complete: Test Generation"
echo ""

# Step 3: Breaking Change Detection
echo "=== Step 3: Breaking Change Detection ==="
echo "Analyzing API changes for breaking modifications..."
echo ""

head_branch=$(gh pr view $PR_NUMBER --json headRefName --jq '.headRefName' 2>/dev/null || echo "unknown")
bash scripts/pr/amp_detect_breaking_changes.sh main $head_branch

echo ""
echo "⚠️  MANUAL STEP REQUIRED: Run the Amp breaking change command shown above"
echo ""
read -p "Press ENTER after running Amp breaking change command... " -r
echo ""

# Collect breaking change results
breaking_uuid=$(cat /tmp/amp_breaking_changes_uuid.txt 2>/dev/null || echo "")
if [ -n "$breaking_uuid" ]; then
    bash scripts/pr/amp_collect_results.sh --timeout 120 --uuids "$breaking_uuid"
    BREAKING_EXIT=$?

    if [ $BREAKING_EXIT -ne 0 ]; then
        echo ""
        echo "⚠️  Potential breaking changes detected. Review carefully."
        if [ $WORKFLOW_EXIT_CODE -eq 0 ]; then
            WORKFLOW_EXIT_CODE=1
        fi
    fi
else
    echo "⚠️  Could not find breaking change UUID. Skipping collection."
fi

echo ""
echo "✅ Step 3 Complete: Breaking Change Detection"
echo ""

# Step 4: Fix Suggestions (Optional)
echo "=== Step 4: Fix Suggestions (Optional) ==="
echo "Do you want to generate fix suggestions based on review comments?"
read -p "Generate fix suggestions? (y/N): " -r GENERATE_FIXES
echo ""

if [[ "$GENERATE_FIXES" =~ ^[Yy]$ ]]; then
    bash scripts/pr/amp_suggest_fixes.sh $PR_NUMBER

    echo ""
    echo "⚠️  MANUAL STEP REQUIRED: Run the Amp fix suggestions command shown above"
    echo ""
    read -p "Press ENTER after running Amp fix suggestions command... " -r
    echo ""

    # Collect fix suggestions
    fixes_uuid=$(cat /tmp/amp_fix_suggestions_uuid_${PR_NUMBER}.txt 2>/dev/null || echo "")
    if [ -n "$fixes_uuid" ]; then
        bash scripts/pr/amp_collect_results.sh --timeout 180 --uuids "$fixes_uuid"
        echo ""
        echo "✅ Fix suggestions available in .claude/amp/responses/consumed/"
    else
        echo "⚠️  Could not find fix suggestions UUID. Skipping collection."
    fi
else
    echo "Skipping fix suggestions."
fi

echo ""
echo "✅ Step 4 Complete: Fix Suggestions"
echo ""

# Final Summary
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))

echo "=================================================================="
echo "        Amp CLI PR Review Workflow Complete"
echo "=================================================================="
echo ""
echo "Total Time: ${TOTAL_TIME}s"
echo ""
echo "Results Summary:"
echo "- Quality Gate: $([ -f /tmp/amp_quality_results.json ] && echo "✅ Complete" || echo "⚠️  Incomplete")"
echo "- Test Generation: $([ -n "$test_uuids" ] && echo "✅ Complete" || echo "⚠️  Skipped")"
echo "- Breaking Changes: $([ -n "$breaking_uuid" ] && echo "✅ Complete" || echo "⚠️  Skipped")"
echo "- Fix Suggestions: $([ -n "$fixes_uuid" ] && echo "✅ Complete" || echo "⚠️  Skipped")"
echo ""

if [ $WORKFLOW_EXIT_CODE -eq 0 ]; then
    echo "🎉 PR #${PR_NUMBER} passed all Amp CLI checks!"
    echo ""
    echo "Next Steps:"
    echo "1. Review generated tests in .claude/amp/responses/consumed/"
    echo "2. Apply fix suggestions if applicable"
    echo "3. Run full test suite: pytest tests/"
    echo "4. Optional: Run gemini-pr-automator for automated review loop"
    echo "   bash scripts/pr/auto_review.sh ${PR_NUMBER} 5 true"
else
    echo "⚠️  PR #${PR_NUMBER} has warnings or issues requiring attention"
    echo ""
    echo "Next Steps:"
    echo "1. Review quality gate results: /tmp/amp_quality_results.json"
    echo "2. Address warnings before requesting review"
    echo "3. Re-run workflow after fixes: bash scripts/pr/amp_pr_review.sh ${PR_NUMBER}"
fi

echo ""
echo "All results saved to:"
echo "- /tmp/amp_quality_results.json"
echo "- .claude/amp/responses/consumed/"
echo ""

exit $WORKFLOW_EXIT_CODE
