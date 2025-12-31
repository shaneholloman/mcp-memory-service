#!/bin/bash
# Check for unused ARG declarations in Dockerfiles
# Prevents issues like #313 where unused ARGs caused confusion

set -e

DOCKERFILES=(
    "tools/docker/Dockerfile"
    "tools/docker/Dockerfile.slim"
)

EXIT_CODE=0

echo "🔍 Checking for unused Docker ARGs..."
echo ""

for dockerfile in "${DOCKERFILES[@]}"; do
    if [[ ! -f "$dockerfile" ]]; then
        echo "⚠️  Skipping $dockerfile (not found)"
        continue
    fi

    echo "📄 Checking $dockerfile"

    # Extract ARG names (excluding built-in TARGETPLATFORM, BUILDPLATFORM, etc.)
    args=$(grep -oP '(?<=^ARG )\w+' "$dockerfile" 2>/dev/null || true)

    for arg in $args; do
        # Skip built-in Docker ARGs that are auto-populated
        case "$arg" in
            TARGETPLATFORM|BUILDPLATFORM|TARGETOS|TARGETARCH|TARGETVARIANT)
                continue
                ;;
        esac

        # Check if ARG is used anywhere (as $ARG or ${ARG} or ${ARG:-default})
        if ! grep -qE "(\\\$$arg|\\$\\{$arg[}:])" "$dockerfile"; then
            echo "   ❌ Unused ARG: $arg"
            EXIT_CODE=1
        else
            echo "   ✅ Used ARG: $arg"
        fi
    done
    echo ""
done

if [[ $EXIT_CODE -eq 0 ]]; then
    echo "✅ All Docker ARGs are used correctly"
else
    echo "❌ Found unused Docker ARGs - please remove them or use them"
    echo ""
    echo "Note: Unused ARGs can cause confusion and build issues."
    echo "See Issue #313 for an example where unused PLATFORM arg"
    echo "caused Apple Silicon builds to fail."
fi

exit $EXIT_CODE
