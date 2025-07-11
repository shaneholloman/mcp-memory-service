# sqlite-vec Integration Research and Implementation Plan

## Executive Summary

This document provides a comprehensive analysis of migrating from ChromaDB to sqlite-vec for the MCP Memory Service, addressing the installation complexity and dependency chain issues identified in Issue #40.

## Current State Analysis

### ChromaDB Implementation Challenges

1. **Complex Installation Process**
   - Heavy dependency chain (torch, transformers, chromadb, etc.)
   - Platform-specific wheel availability issues
   - Binary size: 3-5MB+ with dependencies
   - Memory footprint: High due to multiple dependencies

2. **Installation Pain Points**
   - Windows PyTorch installation issues
   - macOS Intel compatibility problems  
   - Linux ARM64 limited support
   - Docker image size bloat
   - Complex environment setup requirements

### Current Architecture

The existing `ChromaMemoryStorage` class implements:
- **Vector Storage**: ChromaDB collections with embeddings
- **Metadata Management**: Comprehensive metadata tracking
- **Similarity Search**: Semantic search with configurable thresholds
- **Performance Optimizations**: Caching, batching, query optimization
- **Data Management**: Duplicate detection, tagging, time-based queries

## sqlite-vec Analysis

### Key Advantages

1. **Zero Dependencies**
   - Pure C implementation
   - No Python package dependencies beyond sqlite3
   - Binary size: ~300KB (vs 3-5MB for ChromaDB)

2. **Universal Compatibility**
   - Runs anywhere SQLite runs
   - Cross-platform support (Linux, macOS, Windows, WASM)
   - ARM64, x86_64, Raspberry Pi support
   - No platform-specific wheels needed

3. **Installation Simplicity**
   - Single `pip install sqlite-vec` command
   - No complex dependency resolution
   - Works with system Python installations

4. **Performance Characteristics**
   - "Fast enough" for typical use cases
   - Lower memory footprint
   - SQLite's battle-tested reliability
   - Built-in ACID transactions

### Technical Specifications

```python
# Installation
pip install sqlite-vec

# Basic Usage
import sqlite3
import sqlite_vec

db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)

# Vector Operations
from sqlite_vec import serialize_float32
embedding = [0.1, 0.2, 0.3, 0.4]
db.execute('select vec_length(?)', [serialize_float32(embedding)])
```

### Feature Mapping

| Feature | ChromaDB | sqlite-vec | Migration Complexity |
|---------|----------|------------|---------------------|
| Vector Storage | ✅ Collections | ✅ Virtual Tables | Medium |
| Similarity Search | ✅ Built-in | ✅ KNN Search | Low |
| Metadata | ✅ Rich metadata | ✅ Auxiliary columns | Low |
| Batch Operations | ✅ Native | ✅ SQL Transactions | Medium |
| Persistence | ✅ File-based | ✅ SQLite files | Low |
| Embedding Integration | ✅ Custom functions | ⚠️ Manual integration | High |

## Implementation Plan

### Phase 1: Proof of Concept (Week 1)

1. **Create sqlite-vec Storage Backend**
   ```python
   # src/mcp_memory_service/storage/sqlite_vec.py
   class SqliteVecMemoryStorage(MemoryStorage):
       def __init__(self, db_path: str):
           # Initialize SQLite database with vec0 extension
       
       async def store(self, memory: Memory) -> Tuple[bool, str]:
           # Store vector with metadata in virtual table
       
       async def retrieve(self, query: str, n_results: int = 5) -> List[MemoryQueryResult]:
           # Perform KNN search with similarity scoring
   ```

2. **Database Schema Design**
   ```sql
   CREATE VIRTUAL TABLE memories USING vec0(
       content_embedding FLOAT[384],     -- Sentence transformer embeddings
       content_hash TEXT PRIMARY KEY,    -- Content hash for deduplication
       content TEXT,                     -- Original content
       tags TEXT,                        -- JSON array of tags
       timestamp TEXT,                   -- ISO timestamp
       metadata TEXT                     -- JSON metadata
   );
   
   CREATE INDEX idx_content_hash ON memories(content_hash);
   CREATE INDEX idx_timestamp ON memories(timestamp);
   ```

3. **Embedding Integration**
   - Reuse existing sentence-transformers integration
   - Implement manual embedding generation (since sqlite-vec doesn't provide embedding functions)
   - Maintain compatibility with current embedding models

### Phase 2: Feature Parity (Week 2)

1. **Core Operations Implementation**
   - ✅ `store()` - Vector insertion with metadata
   - ✅ `retrieve()` - Semantic similarity search
   - ✅ `search_by_tag()` - Tag-based filtering
   - ✅ `delete()` - Content hash deletion
   - ✅ `delete_by_tag()` - Tag-based deletion

2. **Advanced Features**
   - ✅ Batch operations
   - ✅ Duplicate detection
   - ✅ Time-based queries
   - ✅ Statistics and health monitoring

3. **Performance Optimizations**
   - SQLite query optimization
   - Index management
   - Connection pooling
   - Prepared statements

### Phase 3: Configuration & Testing (Week 3)

1. **Configuration Management**
   ```python
   # Environment variable selection
   STORAGE_BACKEND = os.getenv('MCP_MEMORY_STORAGE_BACKEND', 'chromadb')  # 'chromadb' | 'sqlite-vec'
   ```

2. **Migration Tools**
   ```python
   # Migration utility
   async def migrate_chromadb_to_sqlite_vec(chroma_path: str, sqlite_path: str):
       # Export from ChromaDB and import to sqlite-vec
   ```

3. **Comprehensive Testing**
   - Unit tests for all storage operations
   - Performance benchmarks vs ChromaDB
   - Memory usage analysis
   - Installation testing across platforms

### Phase 4: Production Readiness (Week 4)

1. **Documentation Updates**
   - Installation guide updates
   - Configuration documentation
   - Migration instructions
   - Performance comparison

2. **Docker Configuration**
   - Simplified Dockerfile without ChromaDB dependencies
   - Reduced image size validation
   - Multi-platform testing

3. **Deployment Strategy**
   - Gradual rollout option
   - Backward compatibility
   - Rollback procedures

## Technical Implementation Details

### Vector Storage Schema

```sql
-- Main memories table
CREATE VIRTUAL TABLE memories USING vec0(
    content_embedding FLOAT[384],
    content_hash TEXT,
    content TEXT,
    tags TEXT,
    created_at TEXT,
    updated_at TEXT,
    metadata TEXT
);

-- Additional indexes for performance
CREATE INDEX idx_memories_hash ON memories(content_hash);
CREATE INDEX idx_memories_created ON memories(created_at);
CREATE INDEX idx_memories_tags ON memories(tags);
```

### Query Examples

```python
# Similarity search
async def retrieve(self, query: str, n_results: int = 5):
    query_embedding = await self._generate_embedding(query)
    
    cursor = self.db.execute('''
        SELECT content_hash, content, tags, metadata, distance
        FROM memories
        WHERE content_embedding MATCH ?
        ORDER BY distance
        LIMIT ?
    ''', [serialize_float32(query_embedding), n_results])
    
    return [self._parse_result(row) for row in cursor.fetchall()]

# Tag-based search
async def search_by_tag(self, tags: List[str]):
    tag_conditions = " OR ".join(["json_extract(tags, '$') LIKE ?" for _ in tags])
    tag_params = [f'%"{tag}"%' for tag in tags]
    
    cursor = self.db.execute(f'''
        SELECT content_hash, content, tags, metadata
        FROM memories
        WHERE {tag_conditions}
    ''', tag_params)
```

## Performance Analysis

### Expected Improvements

1. **Installation Time**
   - ChromaDB: 2-5 minutes (with dependencies)
   - sqlite-vec: 10-30 seconds
   - **Improvement**: 80-90% reduction

2. **Memory Usage**
   - ChromaDB: 200-500MB baseline
   - sqlite-vec: 50-100MB baseline
   - **Improvement**: 60-75% reduction

3. **Binary Size**
   - ChromaDB: 50-200MB (with dependencies)
   - sqlite-vec: 1-5MB
   - **Improvement**: 95-98% reduction

4. **Cross-platform Compatibility**
   - ChromaDB: Platform-specific wheels, complex builds
   - sqlite-vec: Universal compatibility
   - **Improvement**: Near-universal compatibility

### Potential Trade-offs

1. **Vector Search Performance**
   - ChromaDB: Optimized for large-scale vector operations
   - sqlite-vec: "Fast enough" for typical use cases (<100K vectors)
   - **Impact**: Potential performance reduction for very large datasets

2. **Feature Richness**
   - ChromaDB: Rich built-in features, embedding functions
   - sqlite-vec: Minimal core, manual integration required
   - **Impact**: More implementation work for advanced features

3. **Ecosystem Integration**
   - ChromaDB: Large ecosystem, extensive documentation
   - sqlite-vec: Smaller ecosystem, pre-v1 status
   - **Impact**: Less community support, potential breaking changes

## Risk Assessment

### High Risk
- **Pre-v1 Status**: sqlite-vec may have breaking changes
- **Performance Regression**: Potential slowdown for large datasets

### Medium Risk
- **Migration Complexity**: Existing user data migration
- **Feature Gaps**: Some ChromaDB features may be hard to replicate

### Low Risk
- **Installation Issues**: sqlite-vec should resolve most installation problems
- **Compatibility**: Better cross-platform support expected

## Recommendation

**Proceed with Implementation** with the following approach:

1. **Parallel Implementation**: Keep ChromaDB as default, add sqlite-vec as optional backend
2. **Gradual Migration**: Allow users to choose backend via configuration
3. **Extensive Testing**: Validate performance and compatibility across platforms
4. **User Feedback**: Gather feedback from early adopters before making it default

This approach provides:
- ✅ **Risk Mitigation**: Maintain existing functionality while adding new option
- ✅ **User Choice**: Let users select based on their needs
- ✅ **Validation**: Real-world testing before full migration
- ✅ **Rollback Path**: Easy reversion if issues arise

## Success Metrics

1. **Installation Success Rate**: Target 95%+ success across platforms
2. **Memory Reduction**: Achieve 60%+ memory usage reduction
3. **Performance Maintenance**: Maintain 90%+ of ChromaDB performance for typical workloads
4. **User Satisfaction**: Positive feedback on installation experience

## Timeline

- **Week 1**: Proof of concept and basic implementation
- **Week 2**: Feature parity and advanced operations
- **Week 3**: Testing, configuration, and migration tools
- **Week 4**: Documentation, deployment, and production readiness

**Total Estimated Effort**: 3-4 weeks for full implementation and testing.