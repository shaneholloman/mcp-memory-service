#!/bin/bash

export MCP_MEMORY_STORAGE_BACKEND=hybrid
export MCP_MEMORY_SQLITE_PATH="/Users/hkr/Library/Application Support/mcp-memory/sqlite_vec.db"
export MCP_HTTP_ENABLED=true
export MCP_OAUTH_ENABLED=false
export CLOUDFLARE_API_TOKEN="Y9qwW1rYkwiE63iWYASxnzfTQlIn-mtwCihRTwZa"
export CLOUDFLARE_ACCOUNT_ID="be0e35a26715043ef8df90253268c33f"
export CLOUDFLARE_D1_DATABASE_ID="f745e9b4-ba8e-4d47-b38f-12af91060d5a"
export CLOUDFLARE_VECTORIZE_INDEX="mcp-memory-index"

cd /Users/hkr/Documents/GitHub/mcp-memory-service
python -m uvicorn mcp_memory_service.web.app:app --host 127.0.0.1 --port 8889 --reload
