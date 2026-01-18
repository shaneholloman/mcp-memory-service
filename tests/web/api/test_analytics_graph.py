# Copyright 2024 Heinrich Krupp
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for Knowledge Graph Dashboard API endpoints (v9.2.0).

Tests the graph analytics endpoints in /api/analytics/:
- /api/analytics/relationship-types
- /api/analytics/graph-visualization
"""

import pytest
import pytest_asyncio
import tempfile
import os
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from mcp_memory_service.web.dependencies import set_storage
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage
from mcp_memory_service.storage.graph import GraphStorage


# Test Fixtures

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_graph.db")
        yield db_path


@pytest_asyncio.fixture
async def initialized_storage(temp_db):
    """Create and initialize a real SQLite storage backend with graph data."""
    storage = SqliteVecMemoryStorage(temp_db)
    await storage.initialize()
    yield storage
    storage.close()


@pytest.fixture
def test_app(initialized_storage, monkeypatch):
    """Create a FastAPI test application with initialized storage."""
    # Disable authentication for tests
    monkeypatch.setenv('MCP_API_KEY', '')
    monkeypatch.setenv('MCP_OAUTH_ENABLED', 'false')
    monkeypatch.setenv('MCP_ALLOW_ANONYMOUS_ACCESS', 'true')

    # Import here to avoid circular dependencies
    from mcp_memory_service.web.app import app

    # Set storage for the app
    set_storage(initialized_storage)

    client = TestClient(app)
    yield client


@pytest_asyncio.fixture
async def storage_with_graph_data(initialized_storage):
    """Populate storage with memories and typed relationships."""
    # Create test memories
    memories = []
    for i in range(10):
        memory = await initialized_storage.store(
            content=f"Test memory {i}",
            tags=["test"],
            memory_type=["note", "observation", "decision"][i % 3]
        )
        memories.append(memory)

    # Create typed relationships using all 6 types
    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    # Symmetric relationships (bidirectional)
    await graph.store_association(
        memories[0], memories[1], 0.8, ["semantic"], relationship_type="related"
    )
    await graph.store_association(
        memories[2], memories[3], 0.7, ["semantic"], relationship_type="contradicts"
    )

    # Asymmetric relationships (directed)
    await graph.store_association(
        memories[4], memories[5], 0.9, ["causal"], relationship_type="causes"
    )
    await graph.store_association(
        memories[6], memories[7], 0.85, ["resolution"], relationship_type="fixes"
    )
    await graph.store_association(
        memories[8], memories[9], 0.75, ["semantic"], relationship_type="supports"
    )
    await graph.store_association(
        memories[0], memories[9], 0.65, ["temporal"], relationship_type="follows"
    )

    # Add some untyped relationships (NULL relationship_type)
    initialized_storage.conn.execute("""
        INSERT INTO memory_graph (source_hash, target_hash, similarity, connection_types, created_at, relationship_type)
        VALUES (?, ?, 0.6, 'semantic', ?, NULL)
    """, (memories[1], memories[2], 1698765432.0))
    initialized_storage.conn.commit()

    yield initialized_storage


# Tests for /api/analytics/relationship-types

@pytest.mark.asyncio
async def test_relationship_type_distribution_empty_database(test_app):
    """Test relationship type distribution with empty database returns empty dict."""
    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_relationship_type_distribution_with_all_six_types(test_app, storage_with_graph_data, monkeypatch):
    """Test distribution with all 6 relationship types (v9.0.0+)."""
    # Re-setup app with populated storage
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)

    # Should have 7 types: 6 typed + 1 untyped
    assert "related" in data
    assert "contradicts" in data
    assert "causes" in data
    assert "fixes" in data
    assert "supports" in data
    assert "follows" in data
    assert "untyped" in data

    # Verify counts (symmetric relationships create 2 edges each)
    assert data["related"] == 2  # Bidirectional
    assert data["contradicts"] == 2  # Bidirectional
    assert data["causes"] == 1  # Directed
    assert data["fixes"] == 1  # Directed
    assert data["supports"] == 1  # Directed
    assert data["follows"] == 1  # Directed
    assert data["untyped"] == 1


@pytest.mark.asyncio
async def test_relationship_type_distribution_only_symmetric(test_app, initialized_storage, monkeypatch):
    """Test distribution with only symmetric relationship types."""
    # Create memories and symmetric relationships
    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    mem1 = await initialized_storage.store("Memory 1", tags=["test"])
    mem2 = await initialized_storage.store("Memory 2", tags=["test"])
    mem3 = await initialized_storage.store("Memory 3", tags=["test"])

    # Only symmetric types
    await graph.store_association(mem1, mem2, 0.8, ["semantic"], relationship_type="related")
    await graph.store_association(mem2, mem3, 0.7, ["semantic"], relationship_type="contradicts")

    set_storage(initialized_storage)

    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()

    # Symmetric relationships create bidirectional edges
    assert data["related"] == 2
    assert data["contradicts"] == 2
    assert len(data) == 2


@pytest.mark.asyncio
async def test_relationship_type_distribution_only_asymmetric(test_app, initialized_storage, monkeypatch):
    """Test distribution with only asymmetric relationship types."""
    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    mem1 = await initialized_storage.store("Decision A", tags=["test"])
    mem2 = await initialized_storage.store("Error B", tags=["test"])
    mem3 = await initialized_storage.store("Fix C", tags=["test"])

    # Only asymmetric types
    await graph.store_association(mem1, mem2, 0.9, ["causal"], relationship_type="causes")
    await graph.store_association(mem3, mem2, 0.85, ["resolution"], relationship_type="fixes")

    set_storage(initialized_storage)

    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()

    # Asymmetric relationships create single directed edges
    assert data["causes"] == 1
    assert data["fixes"] == 1
    assert len(data) == 2


@pytest.mark.asyncio
async def test_relationship_type_distribution_with_untyped_null(test_app, initialized_storage, monkeypatch):
    """Test that NULL relationship_type is returned as 'untyped'."""
    # Create memories
    mem1 = await initialized_storage.store("Memory 1", tags=["test"])
    mem2 = await initialized_storage.store("Memory 2", tags=["test"])

    # Insert untyped relationship directly
    initialized_storage.conn.execute("""
        INSERT INTO memory_graph (source_hash, target_hash, similarity, connection_types, created_at, relationship_type)
        VALUES (?, ?, 0.5, 'semantic', ?, NULL)
    """, (mem1, mem2, 1698765432.0))
    initialized_storage.conn.commit()

    set_storage(initialized_storage)

    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()

    assert "untyped" in data
    assert data["untyped"] == 1


@pytest.mark.asyncio
async def test_relationship_type_distribution_response_format(test_app, storage_with_graph_data, monkeypatch):
    """Test response format matches expected schema (Dict[str, int])."""
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/relationship-types")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure
    assert isinstance(data, dict)
    for rel_type, count in data.items():
        assert isinstance(rel_type, str)
        assert isinstance(count, int)
        assert count > 0


# Tests for /api/analytics/graph-visualization

@pytest.mark.asyncio
async def test_graph_visualization_empty_database(test_app):
    """Test graph visualization with empty database returns empty nodes/edges."""
    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data
    assert len(data["nodes"]) == 0
    assert len(data["edges"]) == 0


@pytest.mark.asyncio
async def test_graph_visualization_basic_structure(test_app, storage_with_graph_data, monkeypatch):
    """Test basic graph visualization structure with populated data."""
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    # Validate structure
    assert "nodes" in data
    assert "edges" in data
    assert "meta" in data

    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    assert isinstance(data["meta"], dict)

    # Should have nodes (memories with connections)
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


@pytest.mark.asyncio
async def test_graph_visualization_node_format(test_app, storage_with_graph_data, monkeypatch):
    """Test that nodes have correct format for D3.js visualization."""
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    for node in data["nodes"]:
        # Required fields for D3.js
        assert "id" in node
        assert "type" in node
        assert "content" in node
        assert "connections" in node
        assert "created_at" in node
        assert "tags" in node

        # Validate types
        assert isinstance(node["id"], str)
        assert isinstance(node["type"], str)
        assert isinstance(node["content"], str)
        assert isinstance(node["connections"], int)
        assert isinstance(node["tags"], list)

        # Content should be truncated to 100 chars
        assert len(node["content"]) <= 100


@pytest.mark.asyncio
async def test_graph_visualization_edge_format(test_app, storage_with_graph_data, monkeypatch):
    """Test that edges have correct format with relationship types."""
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    for edge in data["edges"]:
        # Required fields for D3.js force-directed graph
        assert "source" in edge
        assert "target" in edge
        assert "relationship_type" in edge
        assert "similarity" in edge
        assert "connection_types" in edge

        # Validate types
        assert isinstance(edge["source"], str)
        assert isinstance(edge["target"], str)
        assert isinstance(edge["relationship_type"], str)
        assert isinstance(edge["similarity"], (int, float))
        assert isinstance(edge["connection_types"], str)

        # Relationship type should be one of the 6 types or "related" default
        assert edge["relationship_type"] in [
            "causes", "fixes", "contradicts", "supports", "follows", "related"
        ]


@pytest.mark.asyncio
async def test_graph_visualization_limit_parameter(test_app, initialized_storage, monkeypatch):
    """Test that limit parameter restricts number of nodes returned."""
    # Create many memories with connections
    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    memories = []
    for i in range(20):
        mem = await initialized_storage.store(f"Memory {i}", tags=["test"])
        memories.append(mem)

    # Connect all to first memory (hub topology)
    for i in range(1, 20):
        await graph.store_association(
            memories[0], memories[i], 0.7, ["semantic"], relationship_type="related"
        )

    set_storage(initialized_storage)

    # Test with limit=5
    response = test_app.get("/api/analytics/graph-visualization?limit=5")

    assert response.status_code == 200
    data = response.json()

    assert len(data["nodes"]) <= 5
    assert data["meta"]["limit"] == 5


@pytest.mark.asyncio
async def test_graph_visualization_min_connections_filter(test_app, initialized_storage, monkeypatch):
    """Test that min_connections parameter filters low-connectivity nodes."""
    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    # Create hub with many connections
    hub = await initialized_storage.store("Hub memory", tags=["test"])
    spokes = []
    for i in range(5):
        spoke = await initialized_storage.store(f"Spoke {i}", tags=["test"])
        spokes.append(spoke)
        await graph.store_association(hub, spoke, 0.7, ["semantic"], relationship_type="related")

    # Create isolated pair (only 1 connection each)
    isolated1 = await initialized_storage.store("Isolated 1", tags=["test"])
    isolated2 = await initialized_storage.store("Isolated 2", tags=["test"])
    await graph.store_association(isolated1, isolated2, 0.6, ["semantic"], relationship_type="related")

    set_storage(initialized_storage)

    # Filter to only nodes with 3+ connections
    response = test_app.get("/api/analytics/graph-visualization?min_connections=3")

    assert response.status_code == 200
    data = response.json()

    # Only hub should qualify (has 5 connections)
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["connections"] >= 3
    assert data["meta"]["min_connections"] == 3


@pytest.mark.asyncio
async def test_graph_visualization_meta_information(test_app, storage_with_graph_data, monkeypatch):
    """Test that meta field contains expected metadata."""
    set_storage(storage_with_graph_data)

    response = test_app.get("/api/analytics/graph-visualization?limit=50&min_connections=1")

    assert response.status_code == 200
    data = response.json()

    meta = data["meta"]
    assert "total_nodes" in meta
    assert "total_edges" in meta
    assert "min_connections" in meta
    assert "limit" in meta

    assert meta["total_nodes"] == len(data["nodes"])
    assert meta["total_edges"] == len(data["edges"])
    assert meta["min_connections"] == 1
    assert meta["limit"] == 50


@pytest.mark.asyncio
async def test_graph_visualization_node_colors_by_type(test_app, initialized_storage, monkeypatch):
    """Test that nodes include memory type for color coding."""
    # Create memories with different types
    mem1 = await initialized_storage.store("Note memory", tags=["test"], memory_type="note")
    mem2 = await initialized_storage.store("Decision memory", tags=["test"], memory_type="decision")
    mem3 = await initialized_storage.store("Observation memory", tags=["test"], memory_type="observation")

    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()

    # Connect them
    await graph.store_association(mem1, mem2, 0.8, ["semantic"], relationship_type="related")
    await graph.store_association(mem2, mem3, 0.7, ["semantic"], relationship_type="related")

    set_storage(initialized_storage)

    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    # Verify memory types are preserved for color coding
    types = [node["type"] for node in data["nodes"]]
    assert "note" in types
    assert "decision" in types
    assert "observation" in types


@pytest.mark.asyncio
async def test_graph_visualization_parameter_validation(test_app):
    """Test parameter validation for graph visualization endpoint."""
    # Test invalid limit (< 1)
    response = test_app.get("/api/analytics/graph-visualization?limit=0")
    assert response.status_code == 422  # Validation error

    # Test invalid limit (> 500)
    response = test_app.get("/api/analytics/graph-visualization?limit=1000")
    assert response.status_code == 422

    # Test invalid min_connections (< 1)
    response = test_app.get("/api/analytics/graph-visualization?min_connections=0")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_graph_visualization_handles_deleted_memories(test_app, initialized_storage, monkeypatch):
    """Test that graph visualization excludes soft-deleted memories."""
    # Create memories
    mem1 = await initialized_storage.store("Active memory", tags=["test"])
    mem2 = await initialized_storage.store("Deleted memory", tags=["test"])

    graph = GraphStorage(initialized_storage.db_path)
    await graph._get_connection()
    await graph.store_association(mem1, mem2, 0.8, ["semantic"], relationship_type="related")

    # Soft delete mem2
    await initialized_storage.delete(mem2)

    set_storage(initialized_storage)

    response = test_app.get("/api/analytics/graph-visualization")

    assert response.status_code == 200
    data = response.json()

    # Deleted memory should not appear in nodes
    node_ids = [node["id"] for node in data["nodes"]]
    assert mem2 not in node_ids
