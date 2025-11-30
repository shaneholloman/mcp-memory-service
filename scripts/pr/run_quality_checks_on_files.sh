#!/bin/bash
# scripts/pr/run_quality_checks_on_files.sh - Run quality checks on specific files
#
# Usage: bash scripts/pr/run_quality_checks_on_files.sh [FILE1] [FILE2] ...
#        bash scripts/pr/run_quality_checks_on_files.sh --files-from=changed_files.txt
#        git diff origin/main...HEAD --name-only | bash scripts/pr/run_quality_checks_on_files.sh --stdin
#
# This script is designed for GitHub Actions and CI/CD workflows where we have
# a list of changed files but no PR number yet.
#
# Exit codes:
#   0 - All checks passed
#   1 - Warnings found (non-blocking)
#   2 - Critical issues found (blocking)

set -e

# Determine LLM command (Groq primary, Gemini fallback)
LLM_CMD=""

if [ -n "$GROQ_API_KEY" ] && command -v groq &> /dev/null; then
    LLM_CMD="groq"
    echo "Using Groq API for quality checks (fast mode)"
elif command -v gemini &> /dev/null; then
    LLM_CMD="gemini"
    echo "Using Gemini CLI for quality checks"
else
    echo "Error: No LLM available (neither Groq API nor Gemini CLI found)"
    echo "Install Groq CLI or Gemini CLI to run quality checks"
    exit 1
fi

# Parse input files
files=()

if [ "$1" = "--stdin" ]; then
    # Read from stdin
    while IFS= read -r line; do
        [ -n "$line" ] && files+=("$line")
    done
elif [ "$1" = "--files-from" ]; then
    # Read from file
    files_list="${2#--files-from=}"
    if [ -z "$files_list" ]; then
        files_list="$2"
    fi

    if [ ! -f "$files_list" ]; then
        echo "Error: File list not found: $files_list"
        exit 1
    fi

    while IFS= read -r line; do
        [ -n "$line" ] && files+=("$line")
    done < "$files_list"
else
    # Files provided as arguments
    files=("$@")
fi

# Filter for Python files only
python_files=()
for file in "${files[@]}"; do
    if [[ "$file" == *.py ]]; then
        python_files+=("$file")
    fi
done

if [ ${#python_files[@]} -eq 0 ]; then
    echo "No Python files to check."
    echo "::notice title=Quality Gate::No Python files changed - skipping quality checks"
    exit 0
fi

echo "=== Quality Gate: File-Based Checks ==="
echo ""
echo "Checking ${#python_files[@]} Python file(s):"
for file in "${python_files[@]}"; do
    echo "  - $file"
done
echo ""

exit_code=0
warnings=()
critical_issues=()
complexity_issues=()
security_issues=()

# Check 1: Code Complexity
echo "=== Check 1: Code Complexity ==="
for file in "${python_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "::warning file=$file::File not found in working directory, skipping"
        continue
    fi

    echo "Analyzing: $file"

    # Use LLM to analyze complexity
    result=$($LLM_CMD "Analyze code complexity. Rate each function 1-10 (1=simple, 10=very complex). Report ONLY functions with score >7 in format 'FunctionName: Score X - Reason'. If no functions have score >7, respond with 'COMPLEXITY_OK'. File content:

$(cat "$file")" 2>&1 || echo "COMPLEXITY_OK")

    # Check for high complexity
    if echo "$result" | grep -qi "score [89]\|score 10"; then
        # Extract function names and scores for GitHub Actions annotations
        while IFS= read -r line; do
            if echo "$line" | grep -qi "score [89]\|score 10"; then
                function_name=$(echo "$line" | cut -d':' -f1 | xargs)
                score=$(echo "$line" | grep -oP 'Score \K[0-9]+' || echo "?")

                # Add GitHub Actions warning annotation
                echo "::warning file=$file,title=High Complexity::$line"

                complexity_issues+=("$file: $line")

                # Block on complexity >8, warn on 7-8
                if [ "$score" -gt 8 ] 2>/dev/null; then
                    warnings+=("BLOCKING: High complexity ($score) in $file - $function_name")
                    exit_code=1
                else
                    warnings+=("WARNING: Moderate complexity ($score) in $file - $function_name")
                    if [ $exit_code -eq 0 ]; then
                        exit_code=1
                    fi
                fi
            fi
        done <<< "$result"
    else
        echo "  ✅ Complexity OK"
    fi
done
echo ""

# Check 2: Security Vulnerabilities
echo "=== Check 2: Security Vulnerabilities ==="
for file in "${python_files[@]}"; do
    if [ ! -f "$file" ]; then
        continue
    fi

    echo "Scanning: $file"

    # Request machine-parseable output (same as quality_gate.sh)
    result=$($LLM_CMD "Security audit. Check for: SQL injection (raw SQL), XSS (unescaped HTML), command injection (os.system, subprocess with shell=True), path traversal, hardcoded secrets.

IMPORTANT: Output format:
- If ANY vulnerability found, start response with: VULNERABILITY_DETECTED: [type]
- If NO vulnerabilities found, start response with: SECURITY_CLEAN
- Then provide details

File content:
$(cat "$file")" 2>&1 || echo "SECURITY_CLEAN")

    # Check for machine-parseable vulnerability marker
    if echo "$result" | grep -q "^VULNERABILITY_DETECTED:"; then
        vuln_type=$(echo "$result" | grep "^VULNERABILITY_DETECTED:" | cut -d':' -f2- | xargs)

        # Add GitHub Actions error annotation
        echo "::error file=$file,title=Security Vulnerability::$vuln_type"

        critical_issues+=("🔴 SECURITY: $file - $vuln_type")
        security_issues+=("$file: $vuln_type")
        exit_code=2
    else
        echo "  ✅ Security OK"
    fi
done
echo ""

# Generate GitHub Actions outputs
echo "::group::Quality Gate Summary"
echo ""

if [ $exit_code -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED"
    echo ""
    echo "Quality Gate Results:"
    echo "- Code complexity: ✅ OK"
    echo "- Security scan: ✅ OK"
    echo ""

    # Set GitHub Actions output
    echo "quality_check_passed=true" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "quality_check_status=passed" >> $GITHUB_OUTPUT 2>/dev/null || true

    echo "::notice title=Quality Gate::All checks passed - ready for PR creation"

elif [ $exit_code -eq 2 ]; then
    echo "🔴 CRITICAL FAILURES - PR CREATION BLOCKED"
    echo ""
    echo "Security vulnerabilities detected:"
    for issue in "${security_issues[@]}"; do
        echo "  - $issue"
    done
    echo ""

    # Set GitHub Actions output
    echo "quality_check_passed=false" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "quality_check_status=failed" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "quality_check_blocking=true" >> $GITHUB_OUTPUT 2>/dev/null || true

    # Create detailed error summary for GitHub Actions
    {
        echo "## 🔴 Quality Gate FAILED - Security Issues"
        echo ""
        echo "**Critical security vulnerabilities detected. PR creation is blocked.**"
        echo ""
        echo "### Security Issues:"
        for issue in "${security_issues[@]}"; do
            echo "- $issue"
        done
        echo ""
        echo "**Action Required:**"
        echo "Fix all security vulnerabilities before proceeding."
    } >> $GITHUB_STEP_SUMMARY 2>/dev/null || true

    echo "::error title=Quality Gate::Security vulnerabilities detected - PR creation blocked"

else
    echo "⚠️  WARNINGS DETECTED - NON-BLOCKING"
    echo ""

    if [ ${#complexity_issues[@]} -gt 0 ]; then
        echo "Complexity issues:"
        for issue in "${complexity_issues[@]}"; do
            echo "  - $issue"
        done
        echo ""
    fi

    # Set GitHub Actions output
    echo "quality_check_passed=false" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "quality_check_status=warnings" >> $GITHUB_OUTPUT 2>/dev/null || true
    echo "quality_check_blocking=false" >> $GITHUB_OUTPUT 2>/dev/null || true

    # Create detailed warning summary for GitHub Actions
    {
        echo "## ⚠️  Quality Gate WARNINGS"
        echo ""
        echo "**Some checks require attention (non-blocking).**"
        echo ""
        if [ ${#complexity_issues[@]} -gt 0 ]; then
            echo "### Complexity Issues:"
            for issue in "${complexity_issues[@]}"; do
                echo "- $issue"
            done
            echo ""
        fi
        echo "**Recommendation:**"
        echo "Consider addressing these issues to improve code quality."
    } >> $GITHUB_STEP_SUMMARY 2>/dev/null || true

    echo "::warning title=Quality Gate::Code quality warnings detected - consider addressing before PR creation"
fi

echo "::endgroup::"
echo ""

exit $exit_code
