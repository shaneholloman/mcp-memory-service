# Pull Request Review Guide

This guide provides reviewers with a structured checklist for evaluating pull requests. It ensures consistent review quality and helps catch issues before merging.

## Review Workflow

1. **Initial Triage** (2 minutes) - Check PR template compliance
2. **Code Review** (10-30 minutes) - Review changes for quality and correctness
3. **Testing Verification** (5-15 minutes) - Validate tests and coverage
4. **Documentation Check** (5 minutes) - Ensure docs are updated
5. **Gemini Review** (optional) - Use `/gemini review` for additional analysis
6. **Approval or Request Changes** - Provide clear, actionable feedback

---

## 1. PR Template Compliance

### ✅ Description Quality

- [ ] **Summary Section Present**
  - Clear description of what changes and why
  - Reference to related issue(s): "Fixes #123", "Closes #456"
  - Breaking changes clearly marked

- [ ] **Changes Section Complete**
  - Bullet list of specific changes
  - Technical details for reviewers
  - Impact on existing functionality documented

- [ ] **Testing Section Detailed**
  - Test strategy explained
  - Manual testing steps included (if applicable)
  - Test coverage metrics (if changed)

- [ ] **Screenshots/Examples** (if UI/API changes)
  - Before/after screenshots for UI changes
  - API request/response examples for new endpoints
  - CLI output for new commands

### ✅ Metadata

- [ ] **Labels Applied**
  - `bug`, `feature`, `enhancement`, `docs`, `performance`, etc.
  - `breaking-change` if API/behavior changes
  - `needs-release-notes` if user-visible changes

- [ ] **Milestone Set** (if applicable)
  - Target release version assigned
  - Aligns with project roadmap

- [ ] **Reviewers Assigned**
  - At least one maintainer requested
  - Subject matter experts tagged (if specialized change)

---

## 2. Code Review Standards

### ✅ Type Safety & Documentation

- [ ] **Type Hints Present**
  ```python
  # ✅ Good
  async def store_memory(
      content: str,
      tags: Optional[List[str]] = None,
      metadata: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]:

  # ❌ Bad - no type hints
  async def store_memory(content, tags=None, metadata=None):
  ```

- [ ] **Docstrings Complete**
  - All public functions/classes documented
  - Google-style docstrings with Args/Returns/Raises
  - Complex logic explained

- [ ] **Async Patterns Correct**
  - `async def` for I/O operations
  - `await` used for all async calls
  - No blocking calls in async functions

### ✅ Error Handling

- [ ] **Specific Exception Types**
  ```python
  # ✅ Good
  try:
      result = await storage.store(memory)
  except StorageError as e:
      logger.error(f"Failed to store memory: {e}")
      raise MemoryServiceError(f"Storage operation failed: {e}") from e

  # ❌ Bad - bare except
  try:
      result = await storage.store(memory)
  except:
      pass  # Silently fails
  ```

- [ ] **Error Messages Helpful**
  - Include context (what operation failed)
  - Suggest remediation if possible
  - Don't expose sensitive information

- [ ] **Logging Appropriate**
  - Errors logged with full context
  - Debug logging for troubleshooting
  - No secrets logged

### ✅ Performance Considerations

- [ ] **Database Operations Efficient**
  - Batch operations where possible
  - Indexes used for filters
  - No N+1 query patterns

- [ ] **Caching Appropriate**
  - Global caches (models, embeddings) reused
  - Cache invalidation handled correctly
  - Memory leaks prevented

- [ ] **Async Operations Optimal**
  - Concurrent operations where safe
  - `asyncio.gather()` for parallel tasks
  - Proper timeout handling

### ✅ Security

- [ ] **Input Validation**
  - All user inputs validated
  - SQL injection prevented (parameterized queries)
  - Path traversal prevented (for file operations)

- [ ] **Secrets Management**
  - No hardcoded credentials
  - Environment variables for sensitive config
  - API keys redacted in logs

- [ ] **Authentication/Authorization**
  - API key validation for HTTP endpoints
  - MCP protocol security maintained
  - No bypass vulnerabilities

---

## 3. Testing Verification

### ✅ Test Coverage

- [ ] **Tests Exist for New Code**
  - Unit tests for new functions/classes
  - Integration tests for API changes
  - Regression tests if fixing a bug

- [ ] **Test Quality**
  - Tests are readable and maintainable
  - Mock external dependencies (HTTP, DB, etc.)
  - Test edge cases and error conditions

- [ ] **Coverage Metrics** (aim for >80%)
  ```bash
  pytest --cov=mcp_memory_service tests/
  # Check coverage report for changed files
  ```

### ✅ Test Execution

- [ ] **All Tests Pass**
  - Local: `pytest tests/`
  - CI: All GitHub Actions workflows green
  - No flaky tests introduced

- [ ] **Manual Testing** (if complex change)
  - Reviewer reproduces test scenarios
  - Manual verification of user-facing features
  - Platform-specific testing (if applicable)

### ✅ Regression Prevention

- [ ] **Existing Tests Still Pass**
  - No tests removed or disabled without justification
  - Test fixtures updated if data model changed

- [ ] **Performance Tests** (if performance-critical)
  - Benchmarks show no degradation
  - Scalability verified (e.g., 10K+ memories)

---

## 4. Documentation Updates

### ✅ Code Documentation

- [ ] **CLAUDE.md Updated** (if workflow changes)
  - New commands/scripts documented
  - Essential commands section updated
  - Configuration examples added

- [ ] **CHANGELOG.md Updated**
  - Entry in appropriate section (Added/Fixed/Changed)
  - Follows [Keep a Changelog](https://keepachangelog.com/) format
  - Breaking changes marked clearly

- [ ] **API Documentation** (if API changes)
  - New endpoints documented
  - Request/response examples provided
  - Error codes and messages documented

### ✅ User-Facing Documentation

- [ ] **README.md** (if setup/installation changes)
  - Installation steps updated
  - Configuration examples current
  - Troubleshooting tips added

- [ ] **Wiki Pages** (if major feature)
  - Detailed guide created/updated
  - Examples and use cases provided
  - Cross-linked to related docs

### ✅ Migration Guides

- [ ] **Breaking Changes Documented**
  - Migration path clearly explained
  - Before/after code examples
  - Database migration scripts (if applicable)

- [ ] **Deprecation Notices**
  - Timeline specified (e.g., "removed in v9.0.0")
  - Alternatives recommended
  - Warnings added to deprecated code

---

## 5. Gemini Review Integration

### When to Use `/gemini review`

**Recommended for:**
- Large PRs (>500 lines changed)
- Complex algorithm changes
- Security-critical code
- Performance optimizations
- First-time contributors

**How to Use:**
1. Comment `/gemini review` on the PR
2. Wait ~1 minute for Gemini analysis
3. Review Gemini's findings alongside manual review
4. Address valid concerns, dismiss false positives

### Gemini Review Workflow

**Iteration Cycle:**
1. Contributor pushes changes
2. Maintainer comments with code review feedback
3. `/gemini review` for automated analysis
4. Wait 1 minute for Gemini response
5. Repeat until both human and Gemini reviews pass

**Gemini Strengths:**
- Catches common anti-patterns
- Identifies potential security issues
- Suggests performance improvements
- Validates test coverage

**Gemini Limitations:**
- May flag project-specific patterns as issues
- Context awareness limited (doesn't know full codebase)
- Final decision always with human reviewers

---

## 6. Merge Criteria

### ✅ Must-Have Before Merge

**Code Quality:**
- [ ] All reviewer feedback addressed
- [ ] No unresolved conversations
- [ ] Code follows project style guide

**Testing:**
- [ ] All tests pass (local + CI)
- [ ] New code has adequate test coverage
- [ ] Manual testing completed (if applicable)

**Documentation:**
- [ ] CHANGELOG.md updated
- [ ] User-facing docs updated
- [ ] Breaking changes documented with migration path

**Process:**
- [ ] Branch up-to-date with `main`
- [ ] No merge conflicts
- [ ] Commits follow semantic format

### ✅ Approval Process

**Required Approvals:**
- 1 maintainer approval minimum
- 2 approvals for breaking changes
- Security team approval for security-related changes

**Before Approving:**
- [ ] Reviewer has actually read the code (not just glanced)
- [ ] Tests have been run locally or CI verified
- [ ] Documentation checked for accuracy

### ✅ Merge Method

**Use "Squash and Merge" when:**
- Multiple small commits (WIP, fix typos, etc.)
- Commit history is messy
- Single logical change

**Use "Create a Merge Commit" when:**
- Multiple distinct features in PR
- Each commit is meaningful and well-documented
- Preserving contributor attribution important

**Never use "Rebase and Merge"** (causes issues with CI history)

---

## 7. Common Review Pitfalls

### ❌ Issues to Watch For

**Performance:**
- N+1 queries (loop calling DB for each item)
- Synchronous operations in async code
- Memory leaks (unclosed connections, large caches)

**Security:**
- SQL injection (string concatenation in queries)
- Path traversal (user input in file paths)
- Secrets in code/logs

**Error Handling:**
- Bare `except:` clauses
- Ignoring errors silently
- Cryptic error messages

**Testing:**
- Tests that don't actually test anything
- Flaky tests (timing-dependent, random failures)
- Missing edge cases

**Documentation:**
- Outdated examples
- Missing API documentation
- Breaking changes not highlighted

---

## 8. Providing Effective Feedback

### ✅ Good Feedback Practices

**Be Specific:**
```markdown
# ✅ Good
This function could cause database locks if called concurrently.
Consider adding `PRAGMA busy_timeout=15000` before connection.

# ❌ Bad
This might have issues.
```

**Provide Examples:**
```markdown
# ✅ Good
Consider using async context manager:
\`\`\`python
async with storage.transaction():
    await storage.store(memory)
\`\`\`

# ❌ Bad
Use a transaction here.
```

**Distinguish Required vs. Optional:**
```markdown
# ✅ Good
**Required:** Add type hints to this function.
**Optional (nit):** Consider renaming `tmp` to `temporary_result` for clarity.

# ❌ Bad
Fix these things... [list of both critical and trivial items mixed]
```

**Be Constructive:**
```markdown
# ✅ Good
This implementation works but may be slow with large datasets.
Could we batch the operations? See `batch_store()` in storage.py for an example.

# ❌ Bad
This is terrible, completely wrong approach.
```

### ✅ Review Comment Structure

**For Issues:**
1. State the problem clearly
2. Explain why it's a problem
3. Suggest a solution (or ask for discussion)
4. Link to relevant docs/examples

**For Nitpicks:**
- Prefix with `nit:` or `optional:`
- Don't block merge on nitpicks
- Focus on critical issues first

**For Questions:**
- Ask for clarification on complex logic
- Request comments/docs if unclear
- Verify assumptions

---

## 9. Review Checklist Summary

Copy this checklist into your PR review comment:

```markdown
## Review Checklist

### Template Compliance
- [ ] Description complete with issue references
- [ ] Testing section detailed
- [ ] Labels and milestone set

### Code Quality
- [ ] Type hints and docstrings present
- [ ] Error handling robust
- [ ] Performance considerations addressed
- [ ] Security reviewed (input validation, secrets)

### Testing
- [ ] Tests exist and pass
- [ ] Coverage adequate (>80% for changed code)
- [ ] Manual testing completed (if applicable)

### Documentation
- [ ] CHANGELOG.md updated
- [ ] CLAUDE.md updated (if workflow changes)
- [ ] User-facing docs updated
- [ ] Breaking changes documented

### Process
- [ ] Branch up-to-date with main
- [ ] All CI checks passing
- [ ] Gemini review completed (if applicable)

**Approval Decision:** [ ] Approve | [ ] Request Changes | [ ] Comment
```

---

## 10. Resources

**Project Documentation:**
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guidelines
- [CLAUDE.md](../../CLAUDE.md) - Development workflow
- [Release Checklist](release-checklist.md) - Pre-release testing

**External Resources:**
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Keep a Changelog](https://keepachangelog.com/)
- [Semantic Versioning](https://semver.org/)

**Tools:**
- [Gemini Code Assist for GitHub](https://cloud.google.com/products/gemini/code-assist)
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - Test MCP protocol compliance
- [pytest-cov](https://pytest-cov.readthedocs.io/) - Coverage reporting

---

**Last Updated:** 2025-11-05
**Version:** 1.0
**Related:** [Issue Management Guide](issue-management.md), [Release Checklist](release-checklist.md)
