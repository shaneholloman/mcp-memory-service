#!/bin/bash
# scripts/quality/track_pyscn_metrics.sh - Track pyscn metrics over time
#
# Usage: bash scripts/quality/track_pyscn_metrics.sh
#
# Features:
# - Run pyscn analysis
# - Extract metrics to CSV
# - Store in .pyscn/history/ (gitignored)
# - Compare to previous run
# - Alert on regressions (>5% health score drop)

set -e

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== pyscn Metrics Tracking ===${NC}"
echo ""

# Check for pyscn
if ! command -v pyscn &> /dev/null; then
    echo -e "${RED}❌ pyscn not found${NC}"
    echo "Install with: pip install pyscn"
    exit 1
fi

# Create history directory
mkdir -p .pyscn/history

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE_READABLE=$(date +"%Y-%m-%d %H:%M:%S")

# Run pyscn analysis
echo "Running pyscn analysis..."
REPORT_FILE=".pyscn/reports/analyze_${TIMESTAMP}.html"

if pyscn analyze . --output "$REPORT_FILE" > /tmp/pyscn_metrics.log 2>&1; then
    echo -e "${GREEN}✓${NC} Analysis complete"
else
    echo -e "${RED}❌ Analysis failed${NC}"
    cat /tmp/pyscn_metrics.log
    exit 1
fi

# Extract metrics from HTML report
HEALTH_SCORE=$(grep -o 'Health Score: [0-9]*' "$REPORT_FILE" | head -1 | grep -o '[0-9]*' || echo "0")
COMPLEXITY_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | head -1 | sed 's/<[^>]*>//g' || echo "0")
DEAD_CODE_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | sed -n '2p' | sed 's/<[^>]*>//g' || echo "0")
DUPLICATION_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | sed -n '3p' | sed 's/<[^>]*>//g' || echo "0")
COUPLING_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | sed -n '4p' | sed 's/<[^>]*>//g' || echo "100")
DEPENDENCIES_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | sed -n '5p' | sed 's/<[^>]*>//g' || echo "0")
ARCHITECTURE_SCORE=$(grep -o '<span class="score-value">[0-9]*</span>' "$REPORT_FILE" | sed -n '6p' | sed 's/<[^>]*>//g' || echo "0")

AVG_COMPLEXITY=$(grep -o '<div class="metric-value">[0-9.]*</div>' "$REPORT_FILE" | sed -n '3p' | sed 's/<[^>]*>//g' || echo "0")
MAX_COMPLEXITY=$(grep -o '<div class="metric-value">[0-9]*</div>' "$REPORT_FILE" | sed -n '3p' | sed 's/<[^>]*>//g' || echo "0")
DUPLICATION_PCT=$(grep -o '<div class="metric-value">[0-9.]*%</div>' "$REPORT_FILE" | head -1 | sed 's/<[^>]*>//g' || echo "0%")
DEAD_CODE_ISSUES=$(grep -o '<div class="metric-value">[0-9]*</div>' "$REPORT_FILE" | sed -n '4p' | sed 's/<[^>]*>//g' || echo "0")

echo ""
echo -e "${BLUE}=== Metrics Extracted ===${NC}"
echo "Health Score: $HEALTH_SCORE/100"
echo "Complexity: $COMPLEXITY_SCORE/100 (Avg: $AVG_COMPLEXITY, Max: $MAX_COMPLEXITY)"
echo "Dead Code: $DEAD_CODE_SCORE/100 ($DEAD_CODE_ISSUES issues)"
echo "Duplication: $DUPLICATION_SCORE/100 ($DUPLICATION_PCT)"
echo "Coupling: $COUPLING_SCORE/100"
echo "Dependencies: $DEPENDENCIES_SCORE/100"
echo "Architecture: $ARCHITECTURE_SCORE/100"
echo ""

# Create CSV file if it doesn't exist
CSV_FILE=".pyscn/history/metrics.csv"
if [ ! -f "$CSV_FILE" ]; then
    echo "timestamp,date,health_score,complexity_score,dead_code_score,duplication_score,coupling_score,dependencies_score,architecture_score,avg_complexity,max_complexity,duplication_pct,dead_code_issues" > "$CSV_FILE"
fi

# Append metrics
echo "$TIMESTAMP,$DATE_READABLE,$HEALTH_SCORE,$COMPLEXITY_SCORE,$DEAD_CODE_SCORE,$DUPLICATION_SCORE,$COUPLING_SCORE,$DEPENDENCIES_SCORE,$ARCHITECTURE_SCORE,$AVG_COMPLEXITY,$MAX_COMPLEXITY,$DUPLICATION_PCT,$DEAD_CODE_ISSUES" >> "$CSV_FILE"

echo -e "${GREEN}✓${NC} Metrics saved to $CSV_FILE"
echo ""

# Compare to previous run
if [ $(wc -l < "$CSV_FILE") -gt 2 ]; then
    PREV_HEALTH=$(tail -2 "$CSV_FILE" | head -1 | cut -d',' -f3)
    PREV_DATE=$(tail -2 "$CSV_FILE" | head -1 | cut -d',' -f2)

    echo -e "${BLUE}=== Comparison to Previous Run ===${NC}"
    echo "Previous: $PREV_HEALTH/100 ($(echo "$PREV_DATE" | cut -d' ' -f1))"
    echo "Current:  $HEALTH_SCORE/100 ($(date +%Y-%m-%d))"

    DELTA=$((HEALTH_SCORE - PREV_HEALTH))

    if [ $DELTA -gt 0 ]; then
        echo -e "${GREEN}✅ Improvement: +$DELTA points${NC}"
    elif [ $DELTA -lt 0 ]; then
        ABS_DELTA=${DELTA#-}
        echo -e "${RED}⚠️  Regression: -$ABS_DELTA points${NC}"

        # Alert on significant regression (>5 points)
        if [ $ABS_DELTA -gt 5 ]; then
            echo ""
            echo -e "${RED}🚨 ALERT: Significant quality regression detected!${NC}"
            echo "Health score dropped by $ABS_DELTA points since last check."
            echo ""
            echo "Recommended actions:"
            echo "  1. Review recent changes: git log --since='$PREV_DATE'"
            echo "  2. Compare reports: open $REPORT_FILE"
            echo "  3. Create GitHub issue to track regression"
        fi
    else
        echo -e "${BLUE}➡️  No change${NC}"
    fi
else
    echo -e "${BLUE}ℹ️  No previous metrics for comparison (first run)${NC}"
fi

echo ""
echo -e "${BLUE}=== Trend Summary ===${NC}"
echo "Total measurements: $(tail -n +2 "$CSV_FILE" | wc -l)"
echo "Average health score: $(awk -F',' 'NR>1 {sum+=$3; count++} END {if(count>0) print int(sum/count); else print 0}' "$CSV_FILE")/100"
echo "Highest: $(awk -F',' 'NR>1 {if($3>max || max=="") max=$3} END {print max}' "$CSV_FILE")/100"
echo "Lowest: $(awk -F',' 'NR>1 {if($3<min || min=="") min=$3} END {print min}' "$CSV_FILE")/100"
echo ""

echo -e "${GREEN}✓${NC} Tracking complete"
exit 0
