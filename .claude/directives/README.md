# Claude Code Directives

This directory contains modular directive files that supplement CLAUDE.md with specific behavioral rules and conventions.

## Purpose

- **Keep CLAUDE.md concise** - Move detailed directives here
- **Organize by topic** - Each file covers a specific concern
- **Easy to reference** - Claude can read specific directives when needed
- **Maintainable** - Update directives without bloating main file

## Available Directives

### Core Directives (Always Apply)

- **memory-tagging.md** - CRITICAL: How to tag memories correctly for this project

### Reference Directives (Read When Needed)

- *(Add more as needed - examples below)*
- `release-workflow.md` - Version management, changelog updates, PR workflow
- `code-quality.md` - Quality standards, complexity limits, pre-commit checks
- `testing.md` - Test requirements, coverage expectations
- `documentation.md` - When/where to document (CHANGELOG vs Wiki vs CLAUDE.md)

## How This Works

### In CLAUDE.md

```markdown
## Directives

**IMPORTANT**: Read `.claude/directives/memory-tagging.md` before storing any memories manually.

For detailed directives on specific topics, see `.claude/directives/` directory.
```

### When You Need Guidance

```bash
# Claude automatically reads directives when relevant
# Or explicitly request:
"Check the release workflow directive before creating a release"
"What does the memory tagging directive say?"
```

## Structure Guidelines

Each directive file should:
1. **Start with context** - Why this directive exists
2. **Provide clear rules** - What to do, what NOT to do
3. **Include examples** - Show correct and incorrect usage
4. **Explain consequences** - What breaks if not followed
5. **Keep it concise** - 50-100 lines max per file

## Benefits

✅ **CLAUDE.md stays focused** - High-level overview and essential commands
✅ **Directives are discoverable** - Organized by topic
✅ **Easy to update** - Change one file without context switching
✅ **Context-aware** - Claude reads relevant directives when needed
✅ **Version controlled** - Track directive changes over time
