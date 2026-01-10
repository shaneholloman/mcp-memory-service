# Baseline Complexity Report: install_hooks.py Refactoring

**Analysis Date:** 2026-01-10  
**File:** `claude-hooks/install_hooks.py`  
**Purpose:** Pre-refactoring baseline for complexity reduction project

---

## Executive Summary

Three functions in `install_hooks.py` require refactoring to reduce complexity:

| Function | Priority | Current Complexity | Worst Issue | Target |
|----------|----------|-------------------|-------------|--------|
| `_parse_mcp_get_output` | **P0 (Critical)** | C (12) | 9 nesting levels 🔴🔴 | A (≤6), ≤3 levels |
| `validate_mcp_prerequisites` | **P1 (High)** | C (12) | 12 boolean ops 🔴🔴 | A (≤5), <5 ops |
| `detect_claude_mcp_configuration` | **P2 (Medium)** | B (9) | 5 nesting levels 🔴 | A (≤6), ≤3 levels |

**Overall File Health:**
- Maintainability Index: **C (2.38)** → Target: **B (5.0+)**
- Average Complexity: **B (7.7)** → Target: **A (≤5.0)**

---

## Detailed Metrics

### 1. detect_claude_mcp_configuration() (Lines 198-236)

**Current State:**
- Cyclomatic Complexity: 9 (B grade)
- Nesting Depth: 5 levels
- Total Lines: 39
- Statements: 23
- Control Flow: 3 ifs, 1 for, 4 try/except
- Boolean Operators: 4
- Security: 2 LOW severity issues (subprocess calls)

**Problems:**
- Multiple try/except blocks (4) increase complexity
- Nested exception handling (5 levels deep)
- Mixed concerns: detection + parsing + fallback logic

**Target:** Complexity ≤6 (A), Nesting ≤3 levels

---

### 2. _parse_mcp_get_output() (Lines 238-268)

**Current State:**
- Cyclomatic Complexity: 12 (C grade)
- Nesting Depth: **9 levels** (WORST IN FILE)
- Total Lines: 31
- Statements: 24
- Control Flow: 7 ifs (elif chain), 1 for, 2 try/except
- Boolean Operators: 5

**Problems:**
- **Critical: 9 levels of nesting** (try → for → if → elif chain)
- Long if/elif chain (7 branches) for parsing different fields
- Mixed parsing logic (Status, Type, Command, URL, Scope, Environment)
- Validation logic embedded in parsing

**Target:** Complexity ≤6 (A), Nesting ≤3 levels

---

### 3. validate_mcp_prerequisites() (Lines 351-385)

**Current State:**
- Cyclomatic Complexity: 12 (C grade)
- Nesting Depth: 4 levels
- Total Lines: 35
- Statements: 23
- Control Flow: 8 ifs
- Boolean Operators: **12** (EXCESSIVE)

**Problems:**
- **Critical: 12 boolean operators** (hard to test)
- Multiple validation concerns mixed together
- Validation logic for 3 different server types (stdio, http, unknown)
- Hard-to-test nested conditions

**Target:** Complexity ≤5 (A), Boolean Ops <5

---

## Refactoring Strategy

### Phase 1: _parse_mcp_get_output() (2-3 hours)
1. Extract field parsers into data-driven dictionary
2. Replace if/elif chain with lookup table
3. Reduce nesting from 9 → 3 levels via early returns
4. Separate parsing from validation

**Expected:** C (12) → A (4), Nesting 9 → 3

### Phase 2: validate_mcp_prerequisites() (2-3 hours)
1. Extract validation rules into separate validator functions
2. Replace boolean chains with explicit validation methods
3. Use validation classes (one per server type)
4. Separate concerns: detection → validation → reporting

**Expected:** C (12) → A (5), Boolean ops 12 → 3

### Phase 3: detect_claude_mcp_configuration() (1-2 hours)
1. Extract subprocess calls into dedicated methods
2. Simplify exception handling (use single try/except)
3. Extract fallback logic into separate method
4. Reduce nesting from 5 → 3 levels

**Expected:** B (9) → A (5), Nesting 5 → 3

---

## Success Criteria

### Function-Level Targets

- [ ] `_parse_mcp_get_output`: Complexity ≤6, Nesting ≤3
- [ ] `validate_mcp_prerequisites`: Complexity ≤5, Boolean ops <5
- [ ] `detect_claude_mcp_configuration`: Complexity ≤6, Nesting ≤3

### File-Level Targets

- [ ] Maintainability Index: ≥5.0 (B grade or better)
- [ ] Average Complexity: ≤5.0 (A grade)
- [ ] No new security issues
- [ ] All tests pass
- [ ] Coverage maintained or increased

---

## Measurement Commands

### Baseline (Saved in .metrics/)
```bash
source .venv-analysis/bin/activate
radon cc claude-hooks/install_hooks.py -s -a > .metrics/baseline_cc_install_hooks.txt
radon mi claude-hooks/install_hooks.py -s > .metrics/baseline_mi_install_hooks.txt
python3 /tmp/analyze_functions.py > .metrics/baseline_nesting_install_hooks.txt
```

### After Refactoring
```bash
source .venv-analysis/bin/activate
radon cc claude-hooks/install_hooks.py -s -a > .metrics/after_cc_install_hooks.txt
radon mi claude-hooks/install_hooks.py -s > .metrics/after_mi_install_hooks.txt
python3 /tmp/analyze_functions.py > .metrics/after_nesting_install_hooks.txt

# Compare
diff .metrics/baseline_cc_install_hooks.txt .metrics/after_cc_install_hooks.txt
diff .metrics/baseline_mi_install_hooks.txt .metrics/after_mi_install_hooks.txt
diff .metrics/baseline_nesting_install_hooks.txt .metrics/after_nesting_install_hooks.txt
```

---

## Files

- **Baseline CC:** `.metrics/baseline_cc_install_hooks.txt`
- **Baseline MI:** `.metrics/baseline_mi_install_hooks.txt`
- **Baseline Nesting:** `.metrics/baseline_nesting_install_hooks.txt`
- **Analysis Script:** `/tmp/analyze_functions.py` (for nesting depth)

---

**Next Steps:**
1. Start with Phase 1 (_parse_mcp_get_output) - highest priority
2. Validate improvements after each phase
3. Run full test suite after each refactoring
4. Compare final metrics against baseline

