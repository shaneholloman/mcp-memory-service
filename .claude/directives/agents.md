# Agent Integrations - Detailed Usage

Workflow automation agents using Gemini CLI, Groq API, and Amp CLI.

## Agent Matrix

| Agent | Tool | Purpose | Priority | Usage |
|-------|------|---------|----------|-------|
| **github-release-manager** | GitHub CLI | Complete release workflow | Production | Proactive on feature completion |
| **amp-bridge** | Amp CLI | Research without Claude credits | Production | File-based prompts |
| **code-quality-guard** | Gemini CLI / Groq API | Fast code quality analysis | Active | Pre-commit, pre-PR |
| **gemini-pr-automator** | Gemini CLI | Automated PR review loops | Active | Post-PR creation |

## github-release-manager

**Purpose**: Proactive release workflow automation with issue tracking, version management, and documentation updates.

**Capabilities:**
- **Version Management**: Four-file procedure (__init__.py → pyproject.toml → README.md → uv lock)
- **CHANGELOG Management**: Format guidelines, conflict resolution
- **Documentation Matrix**: Automatic CHANGELOG, CLAUDE.md, README.md updates
- **Issue Tracking**: Auto-detects "fixes #", suggests closures with smart comments
- **Release Procedure**: Merge → Tag → Push → Verify workflows
- **Environment Detection** 🆕: Adapts workflow for local vs GitHub execution

**Usage:**
```bash
# Proactive (agent invokes automatically on feature completion)
@agent github-release-manager "Check if we need a release"

# Manual
@agent github-release-manager "Create release for v8.20.0"
```

**Post-Release Workflow**: Retrieves issues from release, suggests closures with PR links and CHANGELOG entries.

See [`.claude/agents/github-release-manager.md`](../.claude/agents/github-release-manager.md) for complete workflows.

## code-quality-guard

**Purpose**: Fast automated analysis for complexity scoring, security scanning, and refactoring suggestions.

**Capabilities:**
- Complexity check (Gemini CLI or Groq API)
- Security scan (SQL injection, XSS, command injection)
- TODO prioritization
- Pre-commit hook integration

**Usage:**
```bash
# Complexity check (Gemini CLI - default)
gemini "Complexity 1-10 per function, list high (>7) first: $(cat file.py)"

# Complexity check (Groq API - 10x faster, default model)
./scripts/utils/groq "Complexity 1-10 per function: $(cat file.py)"

# Security scan
gemini "Security check (SQL injection, XSS): $(cat file.py)"

# Pre-commit hook (Groq recommended - fast, non-interactive)
export GROQ_API_KEY="your-groq-api-key"
ln -s ../../scripts/hooks/pre-commit .git/hooks/pre-commit
```

**LLM Priority:**
1. **Groq API** (Primary) - 200-300ms, no OAuth browser interruption
2. **Gemini CLI** (Fallback) - 2-3s, OAuth may interrupt commits
3. **Skip checks** - If neither available

See [`.claude/agents/code-quality-guard.md`](../.claude/agents/code-quality-guard.md) for quality standards.

## gemini-pr-automator

**Purpose**: Eliminates manual "Wait 1min → /gemini review" cycles with fully automated review iteration.

**Capabilities:**
- Full automated review (5 iterations, safe fixes enabled)
- Quality gate checks before review
- Test generation for new code
- Breaking change detection

**Usage:**
```bash
# Full automated review
bash scripts/pr/auto_review.sh <PR_NUMBER>

# Quality gate checks
bash scripts/pr/quality_gate.sh <PR_NUMBER>

# Generate tests
bash scripts/pr/generate_tests.sh <PR_NUMBER>

# Breaking change detection
bash scripts/pr/detect_breaking_changes.sh main <BRANCH>
```

**Time Savings**: ~10-30 minutes per PR vs manual iteration.

See [`.claude/agents/gemini-pr-automator.md`](../.claude/agents/gemini-pr-automator.md) for workflows.

## amp-bridge

**Purpose**: File-based workflow for external research without consuming Claude Code credits.

**Usage:**
```bash
# Claude creates prompt → You run command → Amp writes response
amp @.claude/amp/prompts/pending/{uuid}.json
```

**Use cases**: Web research, codebase analysis, documentation generation.

See [docs/amp-cli-bridge.md](../../docs/amp-cli-bridge.md) for architecture.

## Claude Branch Automation 🆕

**Automated workflow** that completes Claude-generated branches with integrated quality checks before PR creation.

**Workflow**: `.github/workflows/claude-branch-automation.yml`

**Flow:**
```
User: "@claude fix issue #254"
    ↓
Claude: Fixes code + Auto-invokes github-release-manager
    ↓
Agent: Creates claude/issue-254-xxx branch with version bump
    ↓
GitHub Actions: Runs uv lock → Quality checks
    ↓
✅ PASS → Creates PR with quality report
❌ FAIL → Comments on issue, blocks PR
```

**Quality Checks:**
1. Code complexity analysis (via Groq/Gemini LLM)
2. Security vulnerability scan
3. Blocks PR if complexity >8 OR security issues found

**Benefits:**
- ✅ Zero bad code in PRs
- ✅ Automated enforcement
- ✅ Fast feedback (<2 minutes)
- ✅ GitHub-native annotations

See workflow: `.github/workflows/claude-branch-automation.yml:95-133`

## Groq Bridge 🔥

**Recommended**: Ultra-fast inference for code-quality-guard agent (~10x faster than Gemini, 200-300ms vs 2-3s).

**Features:**
- Supports multiple models including Kimi K2 (256K context)
- Pre-commit hooks use Groq as primary LLM
- Avoids OAuth browser authentication interruptions

See [`docs/integrations/groq-bridge.md`](../../docs/integrations/groq-bridge.md) for setup.
