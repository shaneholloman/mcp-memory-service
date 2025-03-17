# Windows JSON Parsing Fix

## Issue Description

When running the MCP Memory Service on Windows environments, log messages were incorrectly being treated as JSON-RPC messages by the client, resulting in multiple parsing errors:

```
2025-03-16T19:46:38.795Z [error] [memory] Unexpected token 'U', "Using Chro"... is not valid JSON
2025-03-16T19:46:38.795Z [error] [memory] Unexpected token 'U', "Using back"... is not valid JSON
2025-03-16T19:46:38.796Z [error] [memory] Unexpected token 'I', "[INFO] Star"... is not valid JSON
2025-03-16T19:46:38.796Z [error] [memory] Unexpected token 'I', "[INFO] Foun"... is not valid JSON
2025-03-16T19:46:38.796Z [error] [memory] Unexpected token 'S', "[SUCCESS] S"... is not valid JSON
2025-03-16T19:46:38.796Z [error] [memory] Unexpected token 'I', "[INFO] Call"... is not valid JSON
```

## Root Cause

The issue was caused by:

1. Log messages being sent to stdout, which is also used for JSON-RPC communication
2. Windows-specific stream handling where the stdout and stderr streams were not being properly separated for MCP protocol
3. Lack of stream flushing causing message fragmentation

## Changes Made

The following changes were implemented to fix the issue:

1. Redirected all log messages to stderr instead of stdout:
   - Updated all print functions to explicitly use `file=sys.stderr`
   - Configured Python's logging to use stderr with `stream=sys.stderr`

2. Added explicit flush operations:
   - Added `flush=True` to all print statements to ensure immediate output
   - This prevents buffer mixing between log messages and JSON-RPC communication

3. Files modified:
   - `memory_wrapper.py`
   - `scripts/run_memory_server.py`
   - `src/mcp_memory_service/server.py`

## Technical Details

The MCP protocol uses stdio (standard input/output) for JSON-RPC communication. When log messages are sent to the same stdout stream without proper stream separation, the client attempts to parse these messages as JSON-RPC messages, resulting in the parsing errors.

By redirecting all log messages to stderr, we ensure that the stdout stream contains only valid JSON-RPC messages, which the client can parse correctly.

## Testing

Testing on Windows shows that the service now correctly separates:
- All log messages go to stderr
- Only JSON-RPC communication goes to stdout
- No more "Unexpected token" errors in the client

## Future Considerations

For future development, consider:

1. More robust stream handling with dedicated log files
2. Implementing a custom handler for MCP protocol streams
3. Better error handling for protocol parsing errors