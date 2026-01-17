# Phase 1 Implementation Summary: Memento-Inspired Quality System

## Overview

Successfully implemented Phase 1 (Foundation Layer) of the Memento-Inspired Quality System for Issue #260. This is a **local-first** quality scoring system with multi-tier fallback architecture.

## Architecture

### Tier System

1. **Tier 1 (Primary)**: Local ONNX cross-encoder model (ms-marco-MiniLM-L-6-v2, 23MB)
   - Zero external dependencies
   - 50-100ms latency on CPU, 10-20ms on GPU
   - Automatic GPU detection (CUDA > CoreML > DirectML > CPU)

2. **Tier 2-3 (Optional)**: Groq/Gemini APIs
   - User opt-in only via environment variables
   - Groq integration ready, Gemini placeholder

3. **Tier 4 (Fallback)**: Implicit signals
   - Always available, no dependencies
   - Uses access patterns: frequency, recency, ranking

### Components Implemented

```
src/mcp_memory_service/quality/
├── __init__.py              # Module exports
├── config.py                # Configuration (local-first defaults)
├── onnx_ranker.py           # Tier 1: ONNX cross-encoder
├── implicit_signals.py      # Tier 4: Usage pattern scorer
├── ai_evaluator.py          # Multi-tier coordinator
└── scorer.py                # Composite quality calculator
```

## Key Features

### 1. Quality Configuration (`config.py`)

**Environment Variables:**
- `MCP_QUALITY_SYSTEM_ENABLED` (default: true)
- `MCP_QUALITY_AI_PROVIDER` (default: local, options: local|groq|gemini|auto|none)
- `MCP_QUALITY_LOCAL_MODEL` (default: ms-marco-MiniLM-L-6-v2)
- `MCP_QUALITY_LOCAL_DEVICE` (default: auto, options: auto|cpu|cuda|mps|directml)
- `MCP_QUALITY_BOOST_ENABLED` (default: false)
- `MCP_QUALITY_BOOST_WEIGHT` (default: 0.3)

**Example:**
```python
config = QualityConfig.from_env()
config.validate()
```

### 2. ONNX Ranker (`onnx_ranker.py`)

**Features:**
- Downloads ms-marco-MiniLM-L-6-v2 model from HuggingFace (23MB)
- SHA256 verification for integrity
- Automatic GPU provider detection
- Cross-encoder architecture: processes (query, memory) pairs together
- Returns scores 0.0-1.0 via sigmoid transformation

**Usage:**
```python
from src.mcp_memory_service.quality.onnx_ranker import get_onnx_ranker_model

model = get_onnx_ranker_model(device='auto')
score = model.score_quality(query="Python tutorial", memory_content="Learn Python...")
```

**Model Cache:** `~/.cache/mcp_memory/onnx_models/ms-marco-MiniLM-L-6-v2/`

### 3. Implicit Signals Evaluator (`implicit_signals.py`)

**Signal Components:**
- **Access frequency**: Logarithmic scaling (0-1)
- **Recency**: Exponential decay (30 days → 0.1, 1 day → 0.8)
- **Ranking**: Average position in search results (inverted, so higher rank = higher score)

**Formula:** `0.4 * access_frequency + 0.3 * recency + 0.3 * ranking`

**Usage:**
```python
from src.mcp_memory_service.quality.implicit_signals import ImplicitSignalsEvaluator

evaluator = ImplicitSignalsEvaluator()
score = evaluator.evaluate_quality(memory, query="test")
breakdown = evaluator.get_signal_components(memory)
```

### 4. AI Evaluator (`ai_evaluator.py`)

**Multi-tier Fallback Chain:**
1. Try Local ONNX (if ai_provider='local' or 'auto')
2. Try Groq API (if available and configured)
3. Try Gemini API (if available and configured)
4. Fall back to Implicit Signals (always works)

**Metadata Tracking:**
- `quality_provider`: Which tier scored the memory (e.g., 'onnx_local', 'groq', 'implicit_signals')

**Usage:**
```python
from src.mcp_memory_service.quality.ai_evaluator import QualityEvaluator

evaluator = QualityEvaluator(config)
score = await evaluator.evaluate_quality(query, memory)
```

### 5. Quality Scorer (`scorer.py`)

**Composite Scoring:**
- **Boost disabled**: Use AI score only
- **Boost enabled**: `(1 - boost_weight) * ai_score + boost_weight * implicit_score`

**Metadata Updates:**
- `quality_score`: Final composite score
- `ai_scores`: Historical AI scores (last 10)
- `quality_provider`: Which tier was used
- `quality_components`: Breakdown for debugging

**Usage:**
```python
from src.mcp_memory_service.quality.scorer import QualityScorer

scorer = QualityScorer(config)
score = await scorer.calculate_quality_score(memory, query)
breakdown = scorer.get_score_breakdown(memory)
```

## Memory Model Extensions

**New Properties:**
```python
memory.quality_score        # Final quality score (0.0-1.0)
memory.quality_provider     # Which tier scored it
memory.access_count         # Times accessed
memory.last_accessed_at     # Last access timestamp
```

**New Method:**
```python
memory.record_access(query="test")  # Track access + query
```

**Backward Compatible:** Uses existing `metadata` dict, no schema changes required.

## Storage Backend Integration

**Updated Backends:**
- `sqlite_vec.py`: Added `_persist_access_metadata()` helper
- `cloudflare.py`: Added `_persist_access_metadata()` helper
- `hybrid.py`: Inherits from SQLite, works automatically

**Access Tracking Flow:**
1. User queries memories via `retrieve(query, n_results)`
2. Each retrieved memory calls `memory.record_access(query)`
3. Backend calls `_persist_access_metadata(memory)` to update storage
4. Metadata includes: access_count, last_accessed_at, access_queries (last 10)

## Tests

**Comprehensive Test Suite:** `tests/test_quality_system.py`

**Test Coverage:**
- ✅ Configuration validation (defaults, env vars, validation)
- ✅ Implicit signals evaluation (new, popular, old memories)
- ✅ ONNX ranker initialization and scoring
- ✅ Multi-tier AI evaluator fallback chain
- ✅ Composite quality scorer (with/without boost)
- ✅ Memory access tracking integration
- ✅ Performance benchmarks (implicit <10ms, ONNX <100ms CPU)

**Test Results:**
```bash
$ pytest tests/test_quality_system.py -v
======================== 12 passed, 3 warnings in 6.11s ========================
```

## Performance Targets

| Component | CPU Latency | GPU Latency | Notes |
|-----------|-------------|-------------|-------|
| **Implicit Signals** | <10ms | N/A | Pure Python, no ML |
| **ONNX Ranker** | 50-100ms | 10-20ms | Cross-encoder inference |
| **Composite Scorer** | <10ms | N/A | Score combination overhead |

**Total Overhead:** <110ms per retrieval on CPU (with ONNX), <20ms on GPU

## Local-First Design

**Zero External Calls by Default:**
- Default `ai_provider='local'` uses only ONNX
- Cloud APIs (Groq, Gemini) require explicit opt-in via environment variables
- System works fully offline with local ONNX model + implicit signals

**Graceful Degradation:**
- ONNX unavailable → Fall back to implicit signals
- Cloud API fails → Fall back to ONNX or implicit signals
- Ultimate fallback: implicit signals (always works)

## Next Steps (Phase 2-4)

**Week 3-4: API Integration Layer**
- MCP tool: `/memory-quality-score <query> <content_hash>`
- HTTP endpoint: `POST /api/quality/score`
- Batch scoring for search results

**Week 5-6: Quality-Boosted Retrieval**
- Re-rank search results by quality score
- Weighted combination: `0.7 * semantic_similarity + 0.3 * quality_score`
- User-configurable weights

**Week 7-8: Quality-Based Memory Management**
- Consolidation system integration
- Archive low-quality memories (<0.3 score, 90+ days inactive)
- Promote high-quality memories in search

## Migration Impact

**Backward Compatibility:**
- ✅ No schema changes required
- ✅ Uses existing `metadata` field
- ✅ Existing memories get quality scores on first retrieval
- ✅ System works with or without ONNX Runtime installed

**Zero Breaking Changes:**
- Quality scoring is purely additive
- Storage backends remain compatible
- MCP protocol unchanged (Phase 1)

## Installation

**Dependencies:**
```bash
# Core (no external calls)
pip install numpy  # For ONNX inference

# Optional: Local ONNX scoring (recommended)
pip install onnxruntime tokenizers httpx

# Optional: GPU acceleration
pip install onnxruntime-gpu  # For CUDA
# or use CoreML (macOS), DirectML (Windows) providers

# Optional: Cloud APIs (user opt-in)
export GROQ_API_KEY="your-key"  # For Groq tier
export GEMINI_API_KEY="your-key"  # For Gemini tier (not yet implemented)
```

## Example Usage

```python
import asyncio
from src.mcp_memory_service.quality import QualityConfig, QualityScorer
from src.mcp_memory_service.models.memory import Memory

# Configure local-only scoring
config = QualityConfig(ai_provider='local', boost_enabled=True)
scorer = QualityScorer(config)

# Create memory
memory = Memory(
    content="Python is a high-level programming language with dynamic typing",
    content_hash="python_hash",
    metadata={}
)

# Score quality
async def score_memory():
    score = await scorer.calculate_quality_score(
        memory=memory,
        query="Python programming tutorial"
    )
    print(f"Quality score: {score:.3f}")
    print(f"Provider: {memory.quality_provider}")

    # Get detailed breakdown
    breakdown = scorer.get_score_breakdown(memory)
    print(f"Components: {breakdown}")

asyncio.run(score_memory())
```

## Success Criteria ✅

- ✅ Quality module created with 5 files
- ✅ ONNX ranker downloads and scores correctly (<100ms CPU)
- ✅ Multi-tier fallback chain works (Local → Cloud → Implicit)
- ✅ Memory model extended with quality properties
- ✅ Storage backends track access patterns
- ✅ All unit tests passing (12/12)
- ✅ Zero external API calls by default (local-first)

## Files Changed

**New Files:**
- `/src/mcp_memory_service/quality/__init__.py`
- `/src/mcp_memory_service/quality/config.py`
- `/src/mcp_memory_service/quality/onnx_ranker.py`
- `/src/mcp_memory_service/quality/implicit_signals.py`
- `/src/mcp_memory_service/quality/ai_evaluator.py`
- `/src/mcp_memory_service/quality/scorer.py`
- `/tests/test_quality_system.py`

**Modified Files:**
- `/src/mcp_memory_service/models/memory.py` (added quality properties + `record_access()`)
- `/src/mcp_memory_service/storage/sqlite_vec.py` (added access tracking + `_persist_access_metadata()`)
- `/src/mcp_memory_service/storage/cloudflare.py` (added access tracking + `_persist_access_metadata()`)

**Total:** 7 new files, 3 modified files

---

**Implementation Date:** December 5, 2025
**Issue Reference:** #260 - Memento-Inspired Quality System
**Phase:** 1 (Foundation Layer)
**Status:** ✅ Complete
