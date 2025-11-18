#!/bin/bash
# Safe Cloudflare Update Script
# Pushes corrected timestamps from local SQLite to Cloudflare
# Run this AFTER timestamp restoration, BEFORE re-enabling hybrid on other machines

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "================================================================================"
echo "SAFE CLOUDFLARE UPDATE - Timestamp Recovery"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Verify local database has correct timestamps"
echo "  2. Push corrected timestamps to Cloudflare"
echo "  3. Verify Cloudflare update success"
echo ""
echo "⚠️  IMPORTANT: Run this BEFORE re-enabling hybrid sync on other machines!"
echo ""

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/scripts/sync/sync_memory_backends.py" ]; then
    echo "❌ ERROR: Cannot find sync script. Are you in the project directory?"
    exit 1
fi

# Step 1: Verify local timestamps
echo "================================================================================"
echo "STEP 1: VERIFYING LOCAL TIMESTAMPS"
echo "================================================================================"
echo ""

python3 << 'EOF'
import sqlite3
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from mcp_memory_service import config
    db_path = config.SQLITE_VEC_PATH
except:
    db_path = str(Path.home() / "Library/Application Support/mcp-memory/sqlite_vec.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check total memories
cursor.execute('SELECT COUNT(*) FROM memories')
total = cursor.fetchone()[0]

# Check corruption period (Nov 16-18)
cursor.execute('''
    SELECT COUNT(*) FROM memories
    WHERE created_at_iso LIKE "2025-11-16%"
       OR created_at_iso LIKE "2025-11-17%"
       OR created_at_iso LIKE "2025-11-18%"
''')
corrupted = cursor.fetchone()[0]

corruption_pct = (corrupted * 100 / total) if total > 0 else 0

print(f"Database: {db_path}")
print(f"Total memories: {total}")
print(f"Nov 16-18 dates: {corrupted} ({corruption_pct:.1f}%)")
print()

if corruption_pct < 10:
    print("✅ VERIFICATION PASSED: Timestamps look good")
    print("   Safe to proceed with Cloudflare update")
    conn.close()
    sys.exit(0)
else:
    print("❌ VERIFICATION FAILED: Too many corrupted timestamps")
    print(f"   Expected: <10%, Found: {corruption_pct:.1f}%")
    print()
    print("Run timestamp restoration first:")
    print("  python scripts/maintenance/restore_from_json_export.py --apply")
    conn.close()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Local verification failed. Aborting."
    exit 1
fi

echo ""
read -p "Continue with Cloudflare update? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Update cancelled."
    exit 0
fi

# Step 2: Push to Cloudflare
echo ""
echo "================================================================================"
echo "STEP 2: PUSHING TO CLOUDFLARE"
echo "================================================================================"
echo ""
echo "This will overwrite Cloudflare timestamps with your corrected local data."
echo "Duration: 5-10 minutes (network dependent)"
echo ""

cd "$PROJECT_ROOT"
python scripts/sync/sync_memory_backends.py --direction sqlite-to-cf

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Cloudflare sync failed. Check logs above."
    exit 1
fi

# Step 3: Verify Cloudflare
echo ""
echo "================================================================================"
echo "STEP 3: VERIFYING CLOUDFLARE UPDATE"
echo "================================================================================"
echo ""

python scripts/sync/sync_memory_backends.py --status

echo ""
echo "================================================================================"
echo "UPDATE COMPLETE ✅"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Verify status output above shows expected memory counts"
echo "  2. Check other machines are still offline (hybrid disabled)"
echo "  3. When ready, sync other machines FROM Cloudflare:"
echo "     python scripts/sync/sync_memory_backends.py --direction cf-to-sqlite"
echo ""
echo "See TIMESTAMP_RECOVERY_CHECKLIST.md for detailed next steps."
echo ""
