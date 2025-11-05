# Issue Management Guide

This guide defines the lifecycle of GitHub issues from creation to closure, ensuring consistent triage, tracking, and resolution.

## Issue Lifecycle Overview

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌─────────┐     ┌────────┐
│  Open   │────▶│ Triage  │────▶│ Assigned │────▶│   Fix   │────▶│ Closed │
└─────────┘     └─────────┘     └──────────┘     └─────────┘     └────────┘
    │                                                 │              │
    │                                                 │              │
    └───────────────────── Not Planned ───────────────┴──────────────┘
```

**Typical Timeline:**
- **Triage:** Within 48 hours of creation
- **Assignment:** Within 1 week for prioritized issues
- **Fix:** Depends on severity (critical: 24-48h, normal: 1-4 weeks)
- **Closure:** Immediately after verification in release

---

## 1. Issue Triage Process

### ✅ Initial Triage (within 48 hours)

**For New Issues:**
1. **Verify completeness** - Does issue provide enough information?
   - Bug reports: Reproduction steps, environment, error messages
   - Feature requests: Use case, proposed solution
   - Performance issues: Metrics, database size, environment

2. **Add labels** - Categorize the issue:
   ```
   Type:      bug, feature, enhancement, docs, performance, question
   Priority:  critical, high, medium, low
   Component: storage, mcp, http-api, dashboard, hooks, docs
   Status:    triage, needs-info, blocked, duplicate
   ```

3. **Set initial priority:**
   - **Critical:** Data corruption, security, system unusable
   - **High:** Major functionality broken, significant user impact
   - **Medium:** Feature requests, minor bugs, documentation
   - **Low:** Nice-to-have enhancements, edge cases

4. **Request clarification** (if needed):
   ```markdown
   Thank you for reporting this issue!

   To help us investigate, could you please provide:
   - [ ] Python version (`python --version`)
   - [ ] MCP Memory Service version (`uv run memory --version`)
   - [ ] Storage backend (sqlite-vec / cloudflare / hybrid)
   - [ ] Full error message or stack trace

   This will help us reproduce and fix the issue faster.
   ```

### ✅ Categorization

**Bug Reports:**
- [ ] Verified reproducibility (can maintainer reproduce?)
- [ ] Severity assessed (data loss > broken feature > UI glitch)
- [ ] Affected versions identified
- [ ] Regression or new bug?

**Feature Requests:**
- [ ] Use case clearly defined
- [ ] Aligns with project goals
- [ ] Complexity estimated (small/medium/large)
- [ ] Breaking changes required?

**Performance Issues:**
- [ ] Baseline metrics provided
- [ ] Reproduction steps clear
- [ ] Database size and scale documented
- [ ] Profiling data included (optional but helpful)

### ✅ Duplicate Detection

**Check for duplicates:**
```bash
# Search existing issues
gh issue list --search "keyword in:title,body"
```

**If duplicate found:**
```markdown
This appears to be a duplicate of #123.

Closing as duplicate. Please follow #123 for updates, or comment there if your case has unique details.
```
- [ ] Close as duplicate
- [ ] Add `duplicate` label
- [ ] Link to original issue

---

## 2. Issue-PR Linking

### ✅ Linking Patterns

**In Commit Messages:**
```bash
git commit -m "fix: resolve database lock on concurrent access

Fixes #123
Closes #456"
```

**In PR Descriptions:**
```markdown
## Related Issues
Fixes #123 - Database locking errors
Closes #456 - Concurrent MCP server startup fails
Resolves #789 - Performance degradation with 10K+ memories
```

**Keywords that auto-close:**
- `fixes #123`, `fixed #123`
- `closes #123`, `closed #123`
- `resolves #123`, `resolved #123`

### ✅ Tracking Fix Progress

**While PR is open:**
- [ ] Comment on issue: "Fix in progress via #PR_NUMBER"
- [ ] Add `in-progress` label to issue
- [ ] Update issue with ETA if known

**After PR is merged:**
- [ ] Add `fixed-in-main` label
- [ ] Comment: "Fix merged to main, will be included in next release (v8.x.x)"
- [ ] **Do NOT close yet** - wait for release

---

## 3. Issue Closure Criteria

### ✅ When to Close

**Bug Reports:**
- ✅ Fix verified in release
- ✅ Tests added to prevent regression
- ✅ Documentation updated (if needed)

**Feature Requests:**
- ✅ Feature implemented and released
- ✅ Documentation and examples added
- ✅ Tests cover new functionality

**Questions:**
- ✅ Question answered
- ✅ Solution documented (if common question)
- ✅ 7 days passed with no follow-up

**Not Planned:**
- Out of scope for project
- Duplicate of existing issue
- Cannot reproduce (after clarification attempts)
- Stale (no activity for 60 days after requesting info)

### ✅ Closure Comments (Templates)

**Successful Fix:**
```markdown
✅ **Resolved in v8.x.x** via #PR_NUMBER

This issue has been fixed and released in version 8.x.x.

**What was fixed:**
[Brief description of the fix]

**CHANGELOG Entry:**
[Link to CHANGELOG.md section]

**Additional Resources:**
- [Wiki page if applicable]
- [Migration guide if breaking change]

Thank you for reporting this issue! If you encounter any problems with the fix, please open a new issue.
```

**Feature Implemented:**
```markdown
🎉 **Implemented in v8.x.x** via #PR_NUMBER

This feature has been added and is now available in version 8.x.x.

**How to use:**
\`\`\`bash
# Example usage
uv run memory <new-command>
\`\`\`

**Documentation:**
- [Link to docs/wiki]
- [Example use cases]

**CHANGELOG Entry:**
[Link to CHANGELOG.md section]

Thank you for the suggestion!
```

**Not Planned:**
```markdown
**Closing as "not planned"**

Thank you for the suggestion. After discussion, we've decided not to pursue this for the following reasons:
- [Reason 1: out of scope, conflicts with design goals, etc.]
- [Reason 2: alternative solution exists]

**Alternatives:**
- [Suggest workarounds or related features]

We appreciate your input and welcome other suggestions that align with the project's goals!
```

**Cannot Reproduce:**
```markdown
**Closing as cannot reproduce**

We've attempted to reproduce this issue with the information provided but haven't been able to.

**What we tried:**
- [List reproduction attempts]
- [Environments tested]

If you're still experiencing this issue, please reopen with:
- Minimal reproduction steps
- Full environment details
- Any additional error messages or logs

Thank you for your report!
```

**Duplicate:**
```markdown
**Closing as duplicate of #123**

This issue is a duplicate of #123, which is already being tracked.

Please follow #123 for updates. If your case has unique details not covered there, please comment on that issue with the additional information.

Thank you!
```

### ✅ Post-Closure Actions

- [ ] Add `released` label (if fixed in release)
- [ ] Remove `in-progress` label
- [ ] Update milestone to release version
- [ ] Link to CHANGELOG section
- [ ] Verify issue no longer appears in "open issues" count

---

## 4. Post-Release Issue Review

### ✅ After Each Release

**Systematic Issue Review:**

1. **Find issues fixed in release:**
   ```bash
   # Search for issues with "fixed-in-main" label
   gh issue list --label "fixed-in-main" --state open

   # Or search CHANGELOG for issue references
   grep -E "#[0-9]+" CHANGELOG.md | grep "v8.x.x"
   ```

2. **Verify each issue:**
   - [ ] Fix actually works (test if possible)
   - [ ] User confirmed resolution (if they commented)
   - [ ] No new related issues opened

3. **Close with context:**
   - Use "Resolved in vX.X.X" template (see above)
   - Link to PR and CHANGELOG
   - Add `released` label
   - Thank the reporter

4. **Update documentation:**
   - [ ] Add to Wiki if common issue
   - [ ] Update troubleshooting guide
   - [ ] Remove from known issues list

### ✅ Issue Closure Checklist

```markdown
## Post-Release Issue Closure

**Release:** v8.x.x
**Date:** 2025-11-05

### Issues Fixed in This Release
- [ ] #123 - Database locking on concurrent access
  - [x] Fix verified
  - [x] User notified
  - [x] Closed with CHANGELOG link
  - [x] `released` label added

- [ ] #456 - Performance degradation with 10K memories
  - [x] Fix verified
  - [x] Benchmarks updated
  - [x] Closed with Wiki link
  - [x] `released` label added

### Documentation Updates
- [ ] Wiki updated with new troubleshooting steps
- [ ] FAQ updated with common questions from issues
- [ ] Removed resolved issues from "Known Issues" section

### Follow-up
- [ ] Monitor for new related issues (1 week)
- [ ] Update roadmap if priorities changed
```

---

## 5. Label System

### Primary Labels

**Type Labels** (choose one):
- `bug` - Something isn't working
- `feature` - New feature request
- `enhancement` - Improvement to existing feature
- `docs` - Documentation changes
- `performance` - Performance-related issue
- `question` - Question or discussion

**Priority Labels** (choose one):
- `critical` - Blocking, data loss, security
- `high` - Major functionality affected
- `medium` - Standard priority
- `low` - Nice-to-have, edge case

**Component Labels** (multiple allowed):
- `storage` - Storage backend (sqlite/cloudflare/hybrid)
- `mcp` - MCP protocol, tools, server
- `http-api` - HTTP server, REST API, dashboard
- `hooks` - Claude Code hooks, integrations
- `docs` - Documentation files
- `testing` - Test infrastructure

**Status Labels**:
- `triage` - Needs initial review
- `needs-info` - Waiting for reporter clarification
- `in-progress` - Fix is being worked on
- `fixed-in-main` - Merged to main, not yet released
- `released` - Included in a release
- `blocked` - Cannot proceed (dependency, design decision)
- `duplicate` - Duplicate of another issue
- `wontfix` - Not planned

**Special Labels**:
- `breaking-change` - Requires migration, major version bump
- `needs-release-notes` - Should be highlighted in release
- `good-first-issue` - Suitable for new contributors
- `help-wanted` - Community contributions welcome
- `regression` - Previously working functionality broken

### Label Usage Examples

**Bug Report (Critical):**
```
Labels: bug, critical, storage, triage
Priority: Handle within 24-48 hours
```

**Feature Request (Low Priority):**
```
Labels: feature, low, http-api, help-wanted
Priority: Community contribution or backlog
```

**Performance Issue (High Priority):**
```
Labels: performance, high, storage, needs-info
Priority: Needs profiling data, then fix within 1-2 weeks
```

---

## 6. Automation with GitHub CLI

### Useful Commands

**List issues by label:**
```bash
# Critical bugs
gh issue list --label bug,critical

# In-progress features
gh issue list --label feature,in-progress

# Needs triage
gh issue list --label triage
```

**Bulk label operations:**
```bash
# Add label to multiple issues
gh issue edit 123 456 789 --add-label released

# Remove label
gh issue edit 123 --remove-label in-progress
```

**Close multiple issues:**
```bash
# Close issues fixed in release
gh issue close 123 456 789 --comment "Resolved in v8.x.x. See CHANGELOG for details."
```

**Create issue from command line:**
```bash
gh issue create \
  --title "Bug: Database lock on concurrent access" \
  --body "$(cat bug-report.md)" \
  --label bug,critical,storage
```

---

## 7. Special Scenarios

### ✅ Long-Running Issues

**For issues open >30 days:**
- [ ] Weekly check-in comment with progress update
- [ ] Break into smaller sub-tasks if too large
- [ ] Consider adding to project board
- [ ] Reassign if stalled

**Progress Update Template:**
```markdown
**Status Update - Week X**

**Progress:**
- [What's been completed]
- [Current blockers]

**Next Steps:**
- [ ] Task 1
- [ ] Task 2

**ETA:** Target v8.x.x release
```

### ✅ User Follow-up Needed

**If more info needed:**
```markdown
**Needs More Information**

To investigate this issue, we need:
- [ ] [Specific info 1]
- [ ] [Specific info 2]

Please provide these details at your convenience. This issue will be automatically closed if there's no response within 14 days.

Thank you!
```

**Add labels:**
- `needs-info`
- Set reminder to follow up in 14 days

### ✅ Stale Issues

**After 60 days of inactivity (needs-info):**
```markdown
**Closing due to inactivity**

This issue is being closed because we haven't received the requested information after 60 days.

If you're still experiencing this problem, please open a new issue with:
- Updated environment details
- Current reproduction steps
- Any additional context

Thank you!
```

---

## 8. Integration with Release Process

### Release Preparation

**1-2 weeks before release:**
- [ ] Review all `in-progress` issues
- [ ] Verify linked PRs are merged
- [ ] Add `fixed-in-main` label to merged fixes

**During release:**
- [ ] Include issue references in CHANGELOG
- [ ] Link issues in release notes
- [ ] Prepare issue closure comments

**After release:**
- [ ] Close all `fixed-in-main` issues
- [ ] Add `released` label
- [ ] Verify no regressions reported

### Issue→PR→Release Tracking

**Example flow:**
1. User reports #123 "Database lock error"
2. Issue triaged: `bug`, `high`, `storage`
3. PR #456 created: "Fixes #123"
4. PR merged → add `fixed-in-main` to #123
5. v8.17.0 released → close #123 with release notes
6. Add `released` label to #123

---

## 9. Communication Best Practices

### ✅ Response Time Expectations

- **Critical bugs:** Response within 24 hours
- **High priority:** Response within 48 hours
- **Medium/Low:** Response within 1 week
- **Questions:** Response within 2-3 days

### ✅ Tone and Language

**Be welcoming:**
```markdown
# ✅ Good
Thank you for reporting this! We'll investigate and get back to you shortly.

# ❌ Bad
Why didn't you search for duplicates first?
```

**Be specific:**
```markdown
# ✅ Good
This issue occurs because SQLite doesn't handle concurrent writes with default settings.
The fix will add PRAGMA busy_timeout to prevent lock errors.

# ❌ Bad
We'll look into this.
```

**Be transparent:**
```markdown
# ✅ Good
This is a complex change that will require significant refactoring.
ETA: v9.0.0 (3-4 months). We'll keep you updated on progress.

# ❌ Bad
We'll fix this soon. [then silence for months]
```

### ✅ Escalation Path

**If issue requires architectural decision:**
- Tag `needs-discussion`
- Create GitHub Discussion for community input
- Document decision in issue before implementing

**If issue is out of scope:**
- Explain clearly why
- Suggest alternatives or workarounds
- Offer to help with community fork if valuable

---

## 10. Metrics and Monitoring

### Health Indicators

**Good issue management:**
- <10% of issues in `triage` state
- <20 open issues without labels
- <30 day average time-to-close for bugs
- <5% duplicate rate

**Warning signs:**
- >50 open issues without activity in 30 days
- >10 critical bugs open simultaneously
- Increasing time-to-first-response
- Growing backlog of feature requests

### Monthly Review

**Check these metrics:**
```bash
# Open issues by label
gh issue list --state open --json labels,createdAt | jq -r '.[].labels[].name' | sort | uniq -c

# Issues without labels
gh issue list --state open --json labels | jq 'map(select(.labels | length == 0)) | length'

# Average age of open issues
gh issue list --state open --json createdAt --jq 'map(.createdAt | fromdateiso8601) | add / length / 86400'

# Issues closed this month
gh issue list --state closed --search "closed:>=2025-11-01" --json number | jq 'length'
```

---

## Resources

**GitHub Documentation:**
- [Managing Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues)
- [GitHub CLI Issue Commands](https://cli.github.com/manual/gh_issue)
- [Linking PRs to Issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)

**Project Documentation:**
- [PR Review Guide](pr-review-guide.md)
- [Release Checklist](release-checklist.md)
- [CONTRIBUTING.md](../../CONTRIBUTING.md)

---

**Last Updated:** 2025-11-05
**Version:** 1.0
**Related:** [PR Review Guide](pr-review-guide.md), [Release Checklist](release-checklist.md)
