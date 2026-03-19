# /triage — Security Alert Triage & Remediation

Scan, classify, and fix security alerts for mcp-memory-service.

## Steps

### 1. Scan All Security Alerts

Run these in parallel to gather all alerts:

**Dependabot alerts:**
```bash
gh api repos/{owner}/{repo}/dependabot/alerts --jq '.[] | select(.state=="open") | {number, severity: .security_advisory.severity, package: .security_vulnerability.package.name, summary: .security_advisory.summary, cve: .security_advisory.cve_id}'
```

**CodeQL alerts:**
```bash
gh api repos/{owner}/{repo}/code-scanning/alerts --jq '.[] | select(.state=="open") | {number, severity: .rule.security_severity_level, rule: .rule.id, description: .rule.description, file: .most_recent_instance.location.path}'
```

**Secret scanning alerts:**
```bash
gh api repos/{owner}/{repo}/secret-scanning/alerts --jq '.[] | select(.state=="open") | {number, secret_type: .secret_type_display_name, created_at}'
```

### 2. Classify Each Alert

For each open alert, determine:

| Factor | Assessment |
|--------|------------|
| **Severity** | critical / high / medium / low (from alert data) |
| **Fix complexity** | trivial (dep bump) / moderate (code change) / complex (architecture) |
| **Exploitability** | Is this reachable in our code? Check if the vulnerable code path is actually used |
| **Priority** | Severity × Exploitability → fix order |

Present a summary table sorted by priority (critical first).

### 3. Create Fix Branches and Implement Fixes

For each alert to fix (starting with highest priority):

```bash
# Create fix branch
git checkout -b fix/security-<alert-type>-<number> main

# For Dependabot (dependency bumps):
# Update the dependency in pyproject.toml to the patched version
# Run: pip install -e . && pytest --tb=short -q

# For CodeQL (code fixes):
# Read the flagged file and line
# Implement the fix following the CodeQL recommendation
# Run: pytest --tb=short -q

# For secret scanning:
# Rotate the exposed credential immediately
# Remove from code history if needed
# Update .gitignore / .env.example as needed
```

### 4. Run Tests for Each Fix

```bash
# Quick validation
pytest --tb=short -q

# If security-related, also run:
pytest -m security --tb=short -q 2>/dev/null || true

# Verify no regressions
pytest tests/ --tb=short -q 2>&1 | tail -10
```

If tests fail, investigate and fix before proceeding.

### 5. Open PRs Referencing the Advisory

For each fix branch:
```bash
gh pr create \
  --title "fix(deps): <package> bump for <CVE-ID>" \
  --body "$(cat <<'EOF'
## Security Fix

**Alert**: <alert-type> #<number>
**Severity**: <severity>
**CVE**: <cve-id>
**Advisory**: <GHSA-id>

## Changes
- <description of fix>

## Test Plan
- [ ] All existing tests pass
- [ ] Vulnerability no longer flagged after fix
- [ ] No dependency conflicts introduced

Fixes <advisory-url>
EOF
)" \
  --label "security" \
  --label "dependencies"
```

### 6. Save Fix Patterns to MCP Memory

After each fix, store the pattern using MCP Memory Server:

Content should include:
- Alert type (Dependabot / CodeQL / secret scanning)
- Package or rule affected
- CVE/GHSA identifier
- Fix approach taken
- Whether it was a false positive (and why, if dismissed)
- Tags: `mcp-memory-service`, `security_patterns`, `<alert-type>`, `<severity>`

This builds a knowledge base of fix patterns for faster future triage.

### 7. Handle Known False Positives

Check against known dismissed false positives before creating fixes:
- **CodeQL #365** (`sqlite_vec.py:2095`) — intentional rollback guard
- **CodeQL #357** (`consolidation.py:248`) — sanitized return dict

If an alert matches a known false positive:
1. Dismiss with reason
2. Save dismissal rationale to MCP Memory
3. Skip fix branch creation

## Output Format

Present final triage report:

```
## Security Triage Report — <date>

### Alerts Processed
| # | Type | Severity | Package/Rule | Status | PR |
|---|------|----------|-------------|--------|-----|
| 1 | Dependabot | high | package@ver | Fixed | #NNN |
| 2 | CodeQL | medium | rule-id | False positive | dismissed |
| 3 | Secret | high | API key | Rotated | #NNN |

### Summary
- X alerts fixed, Y dismissed as false positives, Z require manual review
- All fix PRs reference their advisory
- Patterns saved to MCP Memory under `security_patterns` tag
```

## Error Handling
- If `gh api` returns 403: check that the token has `security_events` scope
- If no alerts found: report clean status and save to MCP Memory
- If fix introduces test failures: do NOT open PR, report for manual review
