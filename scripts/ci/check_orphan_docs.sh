#!/usr/bin/env bash
#
# Orphan Doc Check
#
# Fails CI if any newly-added file under docs/ has zero inbound links from
# the rest of the repo (README.md, CLAUDE.md, AGENTS.md, other docs, etc.).
#
# Rationale: avoids the orphan-then-archive cycle (PR #823 wave 1 archived 19
# orphan docs at once). New docs should ship with at least one entry point.
#
# Usage (local):
#   BASE_REF=origin/main bash scripts/ci/check_orphan_docs.sh
#
# Usage (CI):
#   GitHub Actions sets BASE_REF automatically on pull_request events.
#
# Exit codes:
#   0 - All new docs have at least one inbound link, or no new docs
#   1 - One or more new docs are orphans
#   2 - Script error (no base ref / not in repo)

set -euo pipefail

# Resolve base ref: explicit env > GitHub event > origin/main fallback
BASE_REF="${BASE_REF:-}"
if [ -z "$BASE_REF" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
    BASE_REF="origin/$GITHUB_BASE_REF"
fi
if [ -z "$BASE_REF" ]; then
    BASE_REF="origin/main"
fi

# Sanity: are we in a git repo with that ref?
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    echo "⚠️  base ref '$BASE_REF' not found, fetching..."
    git fetch origin --quiet || {
        echo "❌ cannot fetch origin — set BASE_REF explicitly"
        exit 2
    }
fi

# Paths to exempt from the orphan check. Top-level entry docs and intentional
# stand-alone documents that don't need inbound links.
EXEMPT_PATTERNS=(
    "docs/archive/"
    "docs/legacy/"
    "docs/plans/"
    "docs/index.html"
    "docs/.*\.png$"
    "docs/.*\.jpg$"
    "docs/.*\.svg$"
    "docs/.*\.gif$"
    "docs/.*\.css$"
    "docs/.*\.js$"
)

is_exempt() {
    local path="$1"
    for pat in "${EXEMPT_PATTERNS[@]}"; do
        if [[ "$path" =~ $pat ]]; then
            return 0
        fi
    done
    return 1
}

# Collect added docs (status A) under docs/ in the PR diff.
# Bash-3 compatible (macOS): no mapfile; collect into a tmp file.
ADDED_DOCS_FILE=$(mktemp)
trap 'rm -f "$ADDED_DOCS_FILE"' EXIT
git diff --name-only --diff-filter=A "$BASE_REF"...HEAD -- 'docs/**/*.md' >"$ADDED_DOCS_FILE" 2>/dev/null || true

ADDED_COUNT=$(wc -l <"$ADDED_DOCS_FILE" | tr -d ' ')
if [ "$ADDED_COUNT" -eq 0 ]; then
    echo "✅ No new docs added — orphan check skipped"
    exit 0
fi

echo "Checking $ADDED_COUNT new doc(s) for inbound links..."
echo ""

ORPHAN_COUNT=0

while IFS= read -r doc; do
    [ -z "$doc" ] && continue
    if is_exempt "$doc"; then
        echo "  ⏭️  $doc (exempt)"
        continue
    fi

    basename=$(basename "$doc")
    # Strip ".md" so we also match links written without the extension
    stem="${basename%.md}"

    # Search entire repo for inbound references. Look for either:
    #   - the relative path "docs/.../foo.md"
    #   - the basename "foo.md"
    # Exclude the doc itself + its own line in any aggregator file is OK to count.
    refs=$(
        grep -r -l \
            -e "$doc" \
            -e "$basename" \
            --include='*.md' \
            --include='*.html' \
            --include='*.yml' \
            --include='*.yaml' \
            . 2>/dev/null \
        | grep -v "^\./$doc$" \
        | grep -v "^\./docs/archive/" \
        | grep -v "^\./docs/legacy/" \
        || true
    )

    if [ -z "$refs" ]; then
        echo "  ❌ ORPHAN: $doc"
        echo "     No inbound link found from README/CLAUDE.md/other docs."
        ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
    else
        ref_count=$(echo "$refs" | wc -l | tr -d ' ')
        echo "  ✅ $doc (${ref_count} inbound link(s))"
    fi
done <"$ADDED_DOCS_FILE"

echo ""

if [ "$ORPHAN_COUNT" -gt 0 ]; then
    echo "❌ $ORPHAN_COUNT orphan doc(s) detected."
    echo ""
    echo "Each new doc must have at least one inbound link from another file"
    echo "(README.md, CLAUDE.md, AGENTS.md, another doc, or a workflow YAML)."
    echo ""
    echo "Fix options:"
    echo "  1. Add a link from an existing entry-point doc"
    echo "  2. Move to docs/archive/ if intentionally historical"
    echo "  3. Move to docs/plans/ if a working plan (already exempt)"
    exit 1
fi

echo "✅ All new docs have inbound links."
exit 0
