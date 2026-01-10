# /refactor-function Command

Automated function complexity reduction using multi-agent workflow.

## Usage

```bash
# In editor, select a function and run:
/refactor-function

# With options:
/refactor-function --target-complexity 6 --max-helpers 3
/refactor-function --pattern extract-method
/refactor-function --dry-run  # Show plan without applying
```

## Workflow

### 1. Context Extraction
- Detect selected function or function at cursor
- Extract function signature, body, surrounding context
- Parse imports and dependencies

### 2. Baseline Analysis (code-quality-guard)
```
- Measure current complexity
- Identify nesting depth
- Count boolean operators
- Calculate maintainability index
- Generate refactoring targets
```

### 3. Refactoring (amp-bridge)
```
- Apply Extract Method pattern
- Create helper functions
- Reduce nesting with early returns
- Replace if-elif chains with dictionaries
- Extract magic strings to constants
```

### 4. Validation (code-quality-guard)
```
- Measure new complexity
- Verify targets met
- Check for regressions
- Generate diff report
```

### 5. User Review
```
Before:
  Function: parse_output
  Complexity: 12 (C-grade)
  Nesting: 5 levels

After:
  Main: parse_output (C=6, B-grade)
  Helpers:
    - _parse_field (C=4, A-grade)
    - _validate_output (C=3, A-grade)

Apply changes? [y/n]
```

### 6. Optional Commit
```
If applied, offer to commit:
  "refactor: Reduce complexity in <function_name>

  - Complexity: C=12→6 (-50%)
  - Extracted N helpers (avg C=X)
  - Pattern: Extract Method"
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--target-complexity` | Target cyclomatic complexity | 6 |
| `--max-helpers` | Max helper functions to create | 5 |
| `--pattern` | Refactoring pattern | `extract-method` |
| `--dry-run` | Show plan without applying | `false` |
| `--auto-commit` | Commit if successful | `false` |
| `--scope` | Scope (function\|class\|file) | `function` |

## Patterns Supported

1. **extract-method** (default)
   - Extract complex logic to helpers
   - Single Responsibility Principle

2. **early-return**
   - Replace nested if-else with early returns
   - Reduce nesting depth

3. **dictionary-mapping**
   - Replace if-elif chains with dict lookups
   - Reduce cyclomatic complexity

4. **strategy-pattern**
   - Extract validation/processing strategies
   - Improve testability

## Examples

### Example 1: Single Function
```python
# Before
def validate_config(config):
    if not config:
        return False
    if 'host' not in config:
        return False
    if 'port' not in config:
        return False
    # ... 20 more checks
    return True

# After running: /refactor-function --pattern extract-method
def validate_config(config):
    if not config:
        return False

    required_fields = ['host', 'port', ...]
    if not _has_required_fields(config, required_fields):
        return False

    if not _validate_field_types(config):
        return False

    return True

def _has_required_fields(config, fields):
    return all(field in config for field in fields)

def _validate_field_types(config):
    # Extracted validation logic
    ...
```

### Example 2: Class Method
```bash
# Select method in class
/refactor-function --scope method --target-complexity 5
```

### Example 3: Entire File
```bash
/refactor-function --scope file --max-helpers 10 --dry-run
```

## Technical Implementation

### Agent Pipeline
```
User Selection → Parse Context →
code-quality-guard (baseline) →
amp-bridge (refactor) →
code-quality-guard (validate) →
Show Diff → User Approval → Apply
```

### File Structure
```
.claude/commands/
  refactor-function/
    command.json          # Command metadata
    workflow.js           # Orchestration logic
    templates/
      commit-message.txt  # Commit template
      diff-report.md      # Diff template
```

### command.json
```json
{
  "name": "refactor-function",
  "description": "Reduce function complexity using multi-agent refactoring",
  "version": "1.0.0",
  "agents": {
    "baseline": "code-quality-guard",
    "refactor": "amp-bridge",
    "validate": "code-quality-guard"
  },
  "options": {
    "targetComplexity": {
      "type": "number",
      "default": 6,
      "description": "Target cyclomatic complexity"
    },
    "maxHelpers": {
      "type": "number",
      "default": 5,
      "description": "Maximum helper functions to create"
    },
    "pattern": {
      "type": "string",
      "default": "extract-method",
      "enum": ["extract-method", "early-return", "dictionary-mapping", "strategy-pattern"]
    },
    "dryRun": {
      "type": "boolean",
      "default": false,
      "description": "Show plan without applying changes"
    },
    "autoCommit": {
      "type": "boolean",
      "default": false,
      "description": "Automatically commit if successful"
    }
  },
  "requirements": {
    "agents": ["amp-bridge", "code-quality-guard"],
    "tools": ["radon", "git"]
  }
}
```

## Success Metrics

Track command effectiveness:
- Functions refactored: Count
- Average complexity reduction: Percentage
- Success rate: Ratio (applied / attempted)
- Time saved: Estimated hours

## Future Enhancements

1. **Multi-function batch mode**
   ```bash
   /refactor-function --scope file --threshold 10
   # Refactor all functions with C>10
   ```

2. **Interactive helper naming**
   ```
   Proposed helper: _validate_field
   Rename? [Enter to keep, or type new name]
   ```

3. **Test generation**
   ```bash
   /refactor-function --with-tests
   # Generate unit tests for extracted helpers
   ```

4. **Refactoring history**
   ```bash
   /refactor-function --history
   # Show past refactorings and their impact
   ```

## Related Commands

- `/code-review` - Review code quality before refactoring
- `/complexity-report` - Analyze file/module complexity
- `/extract-method` - Manual Extract Method refactoring (no agents)

## Notes

- **Preserves behavior**: All refactorings maintain exact same functionality
- **Version control safe**: Creates commit only if user approves
- **Reversible**: Easily revert with `git revert` if needed
- **Language support**: Python, JavaScript, TypeScript (extensible)

## Credits

Based on proven workflow from Issue #340 (mcp-memory-service):
- 3 functions refactored in 2 hours
- 45.5% complexity reduction
- 100% validation success rate
