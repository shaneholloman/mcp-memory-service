#!/bin/bash
echo "=== Metadata Compression Verification ==="
echo

echo "1. Sync Status:"
curl -s http://127.0.0.1:8000/api/sync/status | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  Failed: {d['operations_failed']} (should be 0)\")"

echo
echo "2. Quality Distribution:"
curl -s http://127.0.0.1:8000/api/quality/distribution | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"  ONNX scored: {d['provider_breakdown'].get('onnx_local', 0)}\")"

echo
echo "3. Recent Logs (compression activity):"
tail -20 /tmp/mcp-http-server.log | grep -i "compress\|too large" || echo "  No compression warnings (good!)"

echo
echo "✅ Verification complete!"
