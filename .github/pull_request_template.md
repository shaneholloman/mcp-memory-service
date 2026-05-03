# Pull Request

## Description

<!-- Provide a clear and concise description of the changes -->

## Motivation

<!-- Explain why these changes are needed and what problem they solve -->

## Type of Change

<!-- Check all that apply -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📝 Documentation update
- [ ] 🧪 Test improvement
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] ⚡ Performance improvement
- [ ] 🔧 Configuration change
- [ ] 🎨 UI/UX improvement

## Changes

<!-- List the specific changes made in this PR -->

-
-
-

**Breaking Changes** (if any):
<!-- Describe any breaking changes and migration steps -->

-

## Testing

### How Has This Been Tested?

<!-- Describe the tests you ran to verify your changes -->

- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing
- [ ] MCP Inspector validation

**Test Configuration**:
- Python version:
- OS:
- Storage backend:
- Installation method:

### Test Coverage

<!-- Describe the test coverage added or modified -->

- [ ] Added new tests
- [ ] Updated existing tests
- [ ] Test coverage maintained/improved

## Regression Prevention (required for Bug fix PRs)

<!--
Goal: prevent the same bug from recurring. Skip ONLY for new-feature PRs that
have no failure mode to lock in.
-->

**What test prevents reintroduction of this bug?**
<!-- File path + test name. e.g. tests/storage/test_sqlite_vec.py::test_deleted_at_guard -->

-

**If no regression test was added, why?**
<!-- Valid reasons: bug is in deprecated code being removed, untestable infra issue,
test infra doesn't yet exist (file follow-up issue and link it). -->

-

## Captured Learnings (recommended)

<!--
Did this PR teach you something non-obvious about the codebase, a library, CI,
or a workflow? Capture it here so the project's memory layer can index it. The
maintainer will save anything useful to the MCP Memory Service with the
appropriate tags. One-line per learning is fine.

Examples (good):
  - SQLite WAL mode requires explicit busy_timeout to survive concurrent writes
    under HTTP+MCP server load (closes the "database is locked" class)
  - peter-evans/create-pull-request must be pinned to SHA, not version tag —
    supply chain finding from PR #578

Skip if there's nothing non-obvious — don't manufacture content.
-->

-

## Related Issues

<!-- Link related issues using keywords: Fixes #123, Closes #456, Relates to #789 -->

Fixes #
Closes #
Relates to #

## Screenshots

<!-- If applicable, add screenshots to help explain your changes -->

## Documentation

<!-- Check all that apply -->

- [ ] Updated README.md
- [ ] Updated CLAUDE.md
- [ ] Updated AGENTS.md
- [ ] Updated CHANGELOG.md
- [ ] Updated Wiki pages
- [ ] Updated code comments/docstrings
- [ ] Added API documentation
- [ ] No documentation needed

## Pre-submission Checklist

<!-- Check all boxes before submitting -->

- [ ] ✅ My code follows the project's coding standards (PEP 8, type hints)
- [ ] ✅ I have performed a self-review of my code
- [ ] ✅ I have commented my code, particularly in hard-to-understand areas
- [ ] ✅ I have made corresponding changes to the documentation
- [ ] ✅ My changes generate no new warnings
- [ ] ✅ I have added tests that prove my fix is effective or that my feature works
- [ ] ✅ New and existing unit tests pass locally with my changes
- [ ] ✅ Any dependent changes have been merged and published
- [ ] ✅ I have updated CHANGELOG.md following [Keep a Changelog](https://keepachangelog.com/) format
- [ ] ✅ I have checked that no sensitive data is exposed (API keys, tokens, passwords)
- [ ] ✅ I have verified this works with all supported storage backends (if applicable)

## Additional Notes

<!-- Any additional information, context, or notes for reviewers -->

---

**For Reviewers**:
- Review checklist: See [Development Reference](https://github.com/doobidoo/mcp-memory-service/wiki/06-Development-Reference)
- Consider testing with Gemini Code Assist for comprehensive review
- Verify CHANGELOG.md entry is present and correctly formatted
- Check documentation accuracy and completeness
