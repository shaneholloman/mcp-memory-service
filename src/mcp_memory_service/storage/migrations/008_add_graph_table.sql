-- Migration 008: Add graph-based memory associations table
-- Supports triple storage modes: memories_only (backward compat), dual_write (migration), graph_only (future)
-- Connection types: semantic (0.3-0.7), temporal (<24h), causal (explicit refs), thematic (shared tags)

CREATE TABLE IF NOT EXISTS memory_graph (
    source_hash TEXT NOT NULL,
    target_hash TEXT NOT NULL,
    similarity REAL NOT NULL,
    connection_types TEXT NOT NULL,  -- JSON array: ["semantic", "temporal", "causal", "thematic"]
    metadata TEXT,                   -- JSON object: {discovery_date, confidence, context}
    created_at REAL NOT NULL,
    PRIMARY KEY (source_hash, target_hash)
);

-- Optimize bidirectional traversal (A→B and B→A queries)
-- Note: PRIMARY KEY already creates an index on (source_hash, target_hash)
CREATE INDEX IF NOT EXISTS idx_graph_source ON memory_graph(source_hash);
CREATE INDEX IF NOT EXISTS idx_graph_target ON memory_graph(target_hash);
