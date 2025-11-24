#!/bin/bash
# scripts/quality/weekly_quality_review.sh - Weekly code quality review
#
# Usage: bash scripts/quality/weekly_quality_review.sh [--create-issue]
#
# Features:
# - Run pyscn analysis
# - Compare to last week's metrics
# - Generate markdown trend report
# - Optionally create GitHub issue if health score dropped >5%

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
CREATE_ISSUE=false
if [ "$1" = "--create-issue" ]; then
    CREATE_ISSUE=true
fi

echo -e "${BLUE}=== Weekly Quality Review ===${NC}"
echo ""

# Run metrics tracking
echo "Running pyscn metrics tracking..."
if bash scripts/quality/track_pyscn_metrics.sh > /tmp/weekly_review.log 2>&1; then
    echo -e "${GREEN}✓${NC} Metrics tracking complete"
else
    echo -e "${RED}❌ Metrics tracking failed${NC}"
    cat /tmp/weekly_review.log
    exit 1
fi

# Extract current and previous metrics
CSV_FILE=".pyscn/history/metrics.csv"

if [ ! -f "$CSV_FILE" ] || [ $(wc -l < "$CSV_FILE") -lt 2 ]; then
    echo -e "${YELLOW}⚠️  Insufficient data for weekly review (need at least 1 previous run)${NC}"
    exit 0
fi

# Get current (last line) and previous (second to last) metrics
CURRENT_LINE=$(tail -1 "$CSV_FILE")
CURRENT_HEALTH=$(echo "$CURRENT_LINE" | cut -d',' -f3)
CURRENT_DATE=$(echo "$CURRENT_LINE" | cut -d',' -f2)
CURRENT_COMPLEXITY=$(echo "$CURRENT_LINE" | cut -d',' -f4)
CURRENT_DUPLICATION=$(echo "$CURRENT_LINE" | cut -d',' -f6)

# Find last week's metrics (7+ days ago)
SEVEN_DAYS_AGO=$(date -v-7d +%Y%m%d 2>/dev/null || date -d "7 days ago" +%Y%m%d)
PREV_LINE=$(awk -F',' -v cutoff="$SEVEN_DAYS_AGO" '$1 < cutoff {last=$0} END {print last}' "$CSV_FILE")

if [ -z "$PREV_LINE" ]; then
    # Fallback to most recent previous entry if no 7-day-old entry exists
    PREV_LINE=$(tail -2 "$CSV_FILE" | head -1)
fi

PREV_HEALTH=$(echo "$PREV_LINE" | cut -d',' -f3)
PREV_DATE=$(echo "$PREV_LINE" | cut -d',' -f2)
PREV_COMPLEXITY=$(echo "$PREV_LINE" | cut -d',' -f4)
PREV_DUPLICATION=$(echo "$PREV_LINE" | cut -d',' -f6)

# Calculate deltas
HEALTH_DELTA=$((CURRENT_HEALTH - PREV_HEALTH))
COMPLEXITY_DELTA=$((CURRENT_COMPLEXITY - PREV_COMPLEXITY))
DUPLICATION_DELTA=$((CURRENT_DUPLICATION - PREV_DUPLICATION))

echo ""
echo -e "${BLUE}=== Weekly Comparison ===${NC}"
echo "Period: $(echo "$PREV_DATE" | cut -d' ' -f1) → $(echo "$CURRENT_DATE" | cut -d' ' -f1)"
echo ""
echo "Health Score:"
echo "  Previous: $PREV_HEALTH/100"
echo "  Current:  $CURRENT_HEALTH/100"
echo "  Change:   $([ $HEALTH_DELTA -ge 0 ] && echo "+")$HEALTH_DELTA points"
echo ""

# Determine overall trend
TREND_EMOJI="➡️"
TREND_TEXT="Stable"

if [ $HEALTH_DELTA -gt 5 ]; then
    TREND_EMOJI="📈"
    TREND_TEXT="Improving"
elif [ $HEALTH_DELTA -lt -5 ]; then
    TREND_EMOJI="📉"
    TREND_TEXT="Declining"
fi

echo -e "${TREND_EMOJI} Trend: ${TREND_TEXT}"
echo ""

# Generate markdown report
REPORT_FILE="docs/development/quality-review-$(date +%Y%m%d).md"
mkdir -p docs/development

cat > "$REPORT_FILE" <<EOF
# Weekly Quality Review - $(date +"%B %d, %Y")

## Summary

**Overall Trend:** ${TREND_EMOJI} ${TREND_TEXT}

| Metric | Previous | Current | Change |
|--------|----------|---------|--------|
| Health Score | $PREV_HEALTH/100 | $CURRENT_HEALTH/100 | $([ $HEALTH_DELTA -ge 0 ] && echo "+")$HEALTH_DELTA |
| Complexity | $PREV_COMPLEXITY/100 | $CURRENT_COMPLEXITY/100 | $([ $COMPLEXITY_DELTA -ge 0 ] && echo "+")$COMPLEXITY_DELTA |
| Duplication | $PREV_DUPLICATION/100 | $CURRENT_DUPLICATION/100 | $([ $DUPLICATION_DELTA -ge 0 ] && echo "+")$DUPLICATION_DELTA |

## Analysis Period

- **Start**: $(echo "$PREV_DATE" | cut -d' ' -f1)
- **End**: $(echo "$CURRENT_DATE" | cut -d' ' -f1)
- **Duration**: ~7 days

## Status

EOF

if [ $CURRENT_HEALTH -lt 50 ]; then
    cat >> "$REPORT_FILE" <<EOF
### 🔴 Critical - Release Blocker

Health score below 50 requires immediate action:
- Cannot merge PRs until resolved
- Focus on refactoring high-complexity functions
- Remove dead code
- Address duplication

**Action Items:**
1. Review full pyscn report: \`.pyscn/reports/analyze_*.html\`
2. Create refactoring tasks for complexity >10 functions
3. Schedule refactoring sprint (target: 2 weeks)
4. Track progress in issue #240

EOF
elif [ $CURRENT_HEALTH -lt 70 ]; then
    cat >> "$REPORT_FILE" <<EOF
### ⚠️  Action Required

Health score 50-69 indicates technical debt accumulation:
- Plan refactoring sprint within 2 weeks
- Review high-complexity functions
- Track improvement progress

**Recommended Actions:**
1. Identify top 5 complexity hotspots
2. Create project board for tracking
3. Allocate 20% of sprint capacity to quality improvements

EOF
else
    cat >> "$REPORT_FILE" <<EOF
### ✅ Acceptable

Health score ≥70 indicates good code quality:
- Continue current development practices
- Monitor trends for regressions
- Address new issues proactively

**Maintenance:**
- Monthly quality reviews
- Track complexity trends
- Keep health score above 70

EOF
fi

# Add trend observations
cat >> "$REPORT_FILE" <<EOF
## Observations

EOF

if [ $HEALTH_DELTA -gt 5 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ✅ **Health score improved by $HEALTH_DELTA points** - Great progress on code quality
EOF
elif [ $HEALTH_DELTA -lt -5 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ⚠️  **Health score declined by ${HEALTH_DELTA#-} points** - Quality regression detected
EOF
fi

if [ $COMPLEXITY_DELTA -gt 0 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ⚠️  Complexity score decreased - New complex code introduced
EOF
elif [ $COMPLEXITY_DELTA -lt 0 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ✅ Complexity score improved - Refactoring efforts paying off
EOF
fi

if [ $DUPLICATION_DELTA -lt 0 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ⚠️  Code duplication increased - Review for consolidation opportunities
EOF
elif [ $DUPLICATION_DELTA -gt 0 ]; then
    cat >> "$REPORT_FILE" <<EOF
- ✅ Code duplication reduced - Good refactoring work
EOF
fi

cat >> "$REPORT_FILE" <<EOF

## Next Steps

1. Review detailed pyscn report for specific issues
2. Update project board with quality improvement tasks
3. Schedule next weekly review for $(date -v+7d +"%B %d, %Y" 2>/dev/null || date -d "7 days" +"%B %d, %Y")

## Resources

- [Full pyscn Report](.pyscn/reports/)
- [Metrics History](.pyscn/history/metrics.csv)
- [Code Quality Workflow](docs/development/code-quality-workflow.md)
- [Issue #240](https://github.com/doobidoo/mcp-memory-service/issues/240) - Quality improvements tracking

EOF

echo -e "${GREEN}✓${NC} Report generated: $REPORT_FILE"
echo ""

# Create GitHub issue if significant regression and flag enabled
if [ "$CREATE_ISSUE" = true ] && [ $HEALTH_DELTA -lt -5 ]; then
    if command -v gh &> /dev/null; then
        echo -e "${YELLOW}Creating GitHub issue for quality regression...${NC}"

        ISSUE_BODY="## Quality Regression Detected

Weekly quality review detected a significant health score decline:

**Health Score Change:** $PREV_HEALTH → $CURRENT_HEALTH (${HEALTH_DELTA} points)

### Details

$(cat "$REPORT_FILE" | sed -n '/## Summary/,/## Next Steps/p' | head -n -1)

### Action Required

1. Review full weekly report: [\`$REPORT_FILE\`]($REPORT_FILE)
2. Investigate recent changes: \`git log --since='$PREV_DATE'\`
3. Prioritize quality improvements in next sprint

### Related

- Issue #240 - Code Quality Improvements
- [pyscn Report](.pyscn/reports/)
"

        gh issue create \
            --title "Weekly Quality Review: Health Score Regression (${HEALTH_DELTA} points)" \
            --body "$ISSUE_BODY" \
            --label "technical-debt,quality"

        echo -e "${GREEN}✓${NC} GitHub issue created"
    else
        echo -e "${YELLOW}⚠️  gh CLI not found, skipping issue creation${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=== Summary ===${NC}"
echo "Review Period: $(echo "$PREV_DATE" | cut -d' ' -f1) → $(echo "$CURRENT_DATE" | cut -d' ' -f1)"
echo "Health Score: $PREV_HEALTH → $CURRENT_HEALTH ($([ $HEALTH_DELTA -ge 0 ] && echo "+")$HEALTH_DELTA)"
echo "Trend: ${TREND_EMOJI} ${TREND_TEXT}"
echo ""
echo "Report: $REPORT_FILE"
echo ""
echo -e "${GREEN}✓${NC} Weekly review complete"
exit 0
