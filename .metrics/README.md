# Complexity Analysis & Refactoring Metrics

**Project:** MCP Memory Service - install_hooks.py Refactoring
**Created:** 2026-01-10
**Purpose:** Track complexity reduction and code quality improvements

---

## Quick Start

### View Current Metrics

```bash
# Cyclomatic Complexity
source .venv-analysis/bin/activate
radon cc claude-hooks/install_hooks.py -s -a

# Maintainability Index
radon mi claude-hooks/install_hooks.py -s

# Nesting Depth (Custom Analysis)
python3 /tmp/analyze_functions.py
```

### Compare Progress

```bash
# Compare complexity
diff baseline_cc_install_hooks.txt after_cc_install_hooks.txt

# Compare maintainability
diff baseline_mi_install_hooks.txt after_mi_install_hooks.txt

# Compare nesting depth
diff baseline_nesting_install_hooks.txt after_nesting_install_hooks.txt
```

---

## Files in This Directory

| File | Purpose | Usage |
|------|---------|-------|
| `BASELINE_REPORT.md` | Comprehensive baseline analysis | Read first for full context |
| `QUICK_REFERENCE.txt` | Quick lookup table | Terminal-friendly summary |
| `TRACKING_TABLE.md` | Progress tracking | Update after each phase |
| `baseline_cc_install_hooks.txt` | Cyclomatic complexity baseline | Compare after refactoring |
| `baseline_mi_install_hooks.txt` | Maintainability index baseline | Compare after refactoring |
| `baseline_nesting_install_hooks.txt` | Nesting depth baseline | Compare after refactoring |
| `README.md` | This file | Usage instructions |

---

## Baseline Summary

### Target Functions

1. **_parse_mcp_get_output()** (Lines 238-268)
   - Priority: P0 (CRITICAL)
   - Complexity: C (12) → Target: A (≤6)
   - Nesting: 9 levels → Target: ≤3 levels
   - Issue: Worst nesting in entire file

2. **validate_mcp_prerequisites()** (Lines 351-385)
   - Priority: P1 (HIGH)
   - Complexity: C (12) → Target: A (≤5)
   - Boolean Ops: 12 → Target: <5
   - Issue: Excessive boolean complexity

3. **detect_claude_mcp_configuration()** (Lines 198-236)
   - Priority: P2 (MEDIUM)
   - Complexity: B (9) → Target: A (≤6)
   - Nesting: 5 levels → Target: ≤3 levels
   - Issue: Over-engineered exception handling

### File-Level Targets

- Maintainability Index: C (2.38) → B (≥5.0)
- Average Complexity: B (7.7) → A (≤5.0)
- Total LOC: 1,454 (expected minor reduction)

---

## Refactoring Phases

### Phase 1: _parse_mcp_get_output() (2-3 hours)
- Extract field parsers into data-driven dictionary
- Replace if/elif chain with lookup table
- Reduce nesting from 9 → 3 levels
- Separate parsing from validation

### Phase 2: validate_mcp_prerequisites() (2-3 hours)
- Extract validation rules into separate validator functions
- Replace boolean chains with explicit validation methods
- Use validation classes (one per server type)
- Separate concerns: detection → validation → reporting

### Phase 3: detect_claude_mcp_configuration() (1-2 hours)
- Extract subprocess calls into dedicated methods
- Simplify exception handling (use single try/except)
- Extract fallback logic into separate method
- Reduce nesting from 5 → 3 levels

**Total Estimated Effort:** 5-8 hours

---

## Success Criteria

### Must Have (Blocking)
- [ ] All 3 functions achieve complexity ≤6 (Grade A)
- [ ] All 3 functions achieve nesting depth ≤3 levels
- [ ] File maintainability index improves to B (≥5.0)
- [ ] No new security issues introduced
- [ ] All existing tests pass

### Should Have (Non-Blocking)
- [ ] Test coverage maintained or increased
- [ ] Boolean operators reduced to <5 in validate_mcp_prerequisites
- [ ] Security issues reduced from 4 → 0
- [ ] Average complexity improves to A (≤5.0)

---

## Validation Workflow

After each refactoring phase:

1. **Run Metrics**
   ```bash
   source .venv-analysis/bin/activate
   radon cc claude-hooks/install_hooks.py -s -a > after_cc_install_hooks.txt
   radon mi claude-hooks/install_hooks.py -s > after_mi_install_hooks.txt
   python3 /tmp/analyze_functions.py > after_nesting_install_hooks.txt
   ```

2. **Compare Results**
   ```bash
   diff baseline_cc_install_hooks.txt after_cc_install_hooks.txt
   diff baseline_mi_install_hooks.txt after_mi_install_hooks.txt
   diff baseline_nesting_install_hooks.txt after_nesting_install_hooks.txt
   ```

3. **Run Tests**
   ```bash
   pytest tests/ -v
   ```

4. **Security Scan**
   ```bash
   bandit -r claude-hooks/install_hooks.py
   ```

5. **Update Tracking**
   - Update `TRACKING_TABLE.md` with current metrics
   - Note any observations or challenges

---

## Tools Used

### Analysis Tools
- **radon** - Cyclomatic complexity and maintainability index
- **bandit** - Security vulnerability scanning
- **Custom AST analyzer** (`/tmp/analyze_functions.py`) - Nesting depth

### Installation
```bash
python3 -m venv .venv-analysis
source .venv-analysis/bin/activate
pip install radon bandit
```

---

## Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Cyclomatic Complexity (worst)** | C (12) | A (≤6) | 50% reduction |
| **Nesting Depth (worst)** | 9 levels | ≤3 levels | 67% reduction |
| **Boolean Operators (worst)** | 12 | <5 | 58% reduction |
| **Maintainability Index (file)** | C (2.38) | B (≥5.0) | 110% increase |
| **Average Complexity (file)** | B (7.7) | A (≤5.0) | 35% reduction |

---

## References

- **Baseline Analysis:** `BASELINE_REPORT.md`
- **Quick Reference:** `QUICK_REFERENCE.txt`
- **Progress Tracking:** `TRACKING_TABLE.md`
- **Project Context:** `/CLAUDE.md` (Code Quality Monitoring section)

---

## Contact & Support

For questions or issues with the refactoring process:
1. Review `BASELINE_REPORT.md` for detailed analysis
2. Check `TRACKING_TABLE.md` for current progress
3. Consult project maintainers if blockers arise

---

**Last Updated:** 2026-01-10
