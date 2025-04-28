@echo off
REM Run Migration Script for MCP Memory Service

echo Starting time-based recall functionality fix...

REM Step 1: Create a backup
echo Creating backup of memory database...
python scripts\backup_memories.py
if %ERRORLEVEL% NEQ 0 (
    echo Warning: Backup operation returned error level %ERRORLEVEL%
    echo This might be a non-critical error. Continuing with migration...
    echo If migration fails, you can manually restore from existing backups if available.
) else (
    echo Backup completed successfully.
)

REM Step 2: Run the migration
echo Running timestamp migration...
python scripts\migrate_timestamps.py
if %ERRORLEVEL% NEQ 0 (
    echo Error during migration. Please check logs.
    exit /b 1
)
echo Migration completed successfully.

echo Time-based recall functionality fix completed. Please restart the MCP Memory Service.
echo See scripts\TIME_BASED_RECALL_FIX.md for detailed information.