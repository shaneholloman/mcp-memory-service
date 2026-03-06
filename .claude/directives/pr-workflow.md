# PR Workflow - Mandatory Quality Checks

## 🚦 Before Creating PR (CRITICAL)

**⚠️ MANDATORY**: Run quality checks BEFORE creating PR to prevent multi-iteration review cycles.

### Recommended Workflow

```bash
# Step 1: Stage your changes
git add .

# Step 2: Run comprehensive pre-PR check (MANDATORY)
bash scripts/pr/pre_pr_check.sh

# Step 3: Only create PR if all checks pass
gh pr create --fill

# Step 4: Request Gemini review
gh pr comment <PR_NUMBER> --body "/gemini review"
```

### What pre_pr_check.sh Does

1. ✅ Runs `quality_gate.sh --staged --with-pyscn` (complexity ≤8, security scan, PEP 8)
2. ✅ Runs full test suite (`pytest tests/`)
3. ✅ Checks import ordering (PEP 8 compliance)
4. ✅ Detects debug code (print statements, breakpoints)
5. ✅ Validates docstring coverage
6. ✅ Reminds to use code-quality-guard agent

### Manual Option (if script unavailable)

```bash
# Run quality gate
bash scripts/pr/quality_gate.sh --staged --with-pyscn

# Run tests
pytest tests/

# Use code-quality-guard agent
@agent code-quality-guard "Analyze complexity and security for staged files"
```

## 🔀 Merging Multiple PRs That Touch the Same Files

When batch-merging several PRs (e.g. community contributions), conflicts arise if they modify the same file.

### Rules

1. **Order first**: identify which PRs share files (`gh pr diff N --name-only`). Merge the base/largest change first, dependents after.
2. **Verify each merge before proceeding**:
   ```bash
   gh pr view N --repo OWNER/REPO --json state,mergedAt
   # state must be "CLOSED" and mergedAt non-null before moving on
   ```
3. **`gh pr merge --auto` does NOT merge immediately** — it only enables auto-merge. Without CI checks to satisfy, the PR stays open silently. Always verify.
4. **If a PR conflicts after earlier merges**: fetch the branch via `git fetch origin 'refs/pull/N/head:local-branch'`, rebase onto current main, push to a new branch, open a substitute PR, merge it, then close the original with an explanation comment.

**Incident (v10.25.0)**: PRs #557, #558, #560 all touched `sqlite_vec.py`. #557 was "merged" with `--auto` but stayed open. #558 and #562 merged next, causing #557 to conflict. Required manual rebase and two substitute PRs (#562, #563).

### Why This Matters

- **PR #280 lesson**: 7 review iterations, 20 issues found across 7 cycles
- **Root cause**: Quality checks NOT run before PR creation
- **Prevention**: Mandatory pre-PR script catches issues early
- **Time saved**: ~30-60 min per PR vs multi-day review cycles

### PR Template Checklist

See `.github/PULL_REQUEST_TEMPLATE.md` for complete checklist including:
- [ ] Quality gate passed (complexity ≤8, no security issues)
- [ ] All tests passing locally
- [ ] Code-quality-guard agent used
- [ ] Self-reviewed on GitHub diff
