#!/bin/bash
# Make this script executable with: chmod +x scripts/run_migration.sh

# Run Migration Script for MCP Memory Service
echo "Starting time-based recall functionality fix..."

# Step 1: Create a backup
echo "Creating backup of memory database..."
python scripts/backup_memories.py
BACKUP_STATUS=$?
if [ $BACKUP_STATUS -ne 0 ]; then
    echo "Warning: Backup operation returned status $BACKUP_STATUS"
    echo "This might be a non-critical error. Continuing with migration..."
    echo "If migration fails, you can manually restore from existing backups if available."
else
    echo "Backup completed successfully."
fi

# Step 2: Run the migration
echo "Running timestamp migration..."
python scripts/migrate_timestamps.py
if [ $? -ne 0 ]; then
    echo "Error during migration. Please check logs."
    exit 1
fi
echo "Migration completed successfully."

echo "Time-based recall functionality fix completed. Please restart the MCP Memory Service."
echo "See scripts/TIME_BASED_RECALL_FIX.md for detailed information."