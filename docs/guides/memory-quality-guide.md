# Memory Quality System Guide

> **Version**: 8.48.3
> **Status**: Production Ready (with known limitations)
> **Feature**: Memento-Inspired Quality System (Issue #260)
> **Evaluation**: [Quality System Evaluation Report](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Quality-System-Evaluation)

## Overview

The **Memory Quality System** transforms MCP Memory Service from static storage to a learning memory system. It automatically evaluates memory quality using AI-driven scoring and uses these scores to improve retrieval precision, consolidation efficiency, and overall system intelligence.

### Key Benefits

- ✅ **40-70% improvement** in retrieval precision (top-5 useful rate: 50% → 70-85%)
- ✅ **Zero cost** with local SLM (privacy-preserving, offline-capable)
- ✅ **Smarter consolidation** - Preserve high-quality memories longer
- ✅ **Quality-boosted search** - Prioritize best memories in results
- ✅ **Automatic learning** - System improves from usage patterns

## How It Works

### Multi-Tier AI Scoring (Local-First)

The system evaluates memory quality (0.0-1.0 score) using a multi-tier fallback chain:

| Tier | Provider | Cost | Latency | Privacy | Default |
|------|----------|------|---------|---------|---------|
| **1** | **Local SLM (ONNX)** | **$0** | **50-100ms** | ✅ Full | ✅ Yes |
| 2 | Groq API | ~$0.30/mo | 900ms | ❌ External | ❌ Opt-in |
| 3 | Gemini API | ~$0.40/mo | 2000ms | ❌ External | ❌ Opt-in |
| 4 | Implicit Signals | $0 | 10ms | ✅ Full | Fallback |

**Default setup**: Local SLM only (zero cost, full privacy, no external API calls)

### Quality Score Components

```
quality_score = (
    local_slm_score × 0.50 +      # Cross-encoder evaluation
    implicit_signals × 0.50        # Usage patterns
)

implicit_signals = (
    access_frequency × 0.40 +      # How often retrieved
    recency × 0.30 +              # When last accessed
    retrieval_ranking × 0.30      # Average position in results
)
```

## ⚠️ ONNX Model Limitations (Important)

**Update (v8.48.3)**: Following comprehensive evaluation with 4,762 memories, we've identified important limitations of the local ONNX model.

### What the Model Is Designed For

The ONNX model (`ms-marco-MiniLM-L-6-v2`) is a **cross-encoder designed for query-document relevance ranking**, NOT absolute quality assessment.

**Intended use**:
```python
# ✅ GOOD: Ranking search results by relevance
query = "How to fix hook connection?"
results = search(query)
ranked = onnx_model.rank(query, results)  # Relative ranking
```

**Not designed for**:
```python
# ❌ PROBLEMATIC: Absolute quality assessment
memory = get_memory("abc123...")
quality = onnx_model.evaluate(memory)  # May produce biased scores
```

### Known Issues

#### 1. Self-Matching Bias

**Problem**: When queries are generated from memory tags during bulk evaluation, they closely match the memory content, producing artificially high scores (~1.0).

**Example**:
```python
# Memory content: "SessionStart hook configuration for hybrid backend..."
# Tags: ["session-start", "hook", "configuration"]
# Generated query: "session start hook configuration"
# Result: Score 1.0 (artificially high due to self-matching)
```

**Impact**: ~25% of memories have perfect 1.0 scores due to this bias.

#### 2. Bimodal Distribution

**Observed**: Many scores cluster at 1.0 (perfect) or near 0.0, with average 0.469 (expected: 0.6-0.7).

**Distribution**:
- High Quality (≥0.7): 32.2% (many are false positives)
- Medium Quality (0.5-0.7): 27.4%
- Low Quality (<0.5): 40.4%

**Root cause**: Model designed for relevance ranking creates binary-like scores when used for absolute quality.

#### 3. No Ground Truth Validation

**Issue**: Without user feedback, we cannot validate if high scores represent genuinely high quality.

**Consequence**: Cannot distinguish between:
- True high-quality memories (useful, accurate, complete)
- Self-matching bias artifacts (high score but average quality)

### Recommended Usage

Based on evaluation results, here's how to use quality scores effectively:

✅ **DO use for**:
- **Relative ranking** within search results (reranking by quality)
- **Comparative analysis** (which memories are better than others)
- **Trend analysis** (is quality improving over time?)
- **Combined scoring** (quality + access patterns + recency)

❌ **DO NOT use for**:
- **Absolute quality thresholds** (e.g., "archive all memories <0.5")
- **Quality-based archival decisions** (without user feedback validation)
- **Ground truth quality labels** (scores may not reflect actual usefulness)

### Workarounds & Solutions

#### Short-Term (Immediate)

1. **Keep quality boost as opt-in** (default: disabled)
   ```bash
   export MCP_QUALITY_BOOST_ENABLED=false  # Current default
   ```

2. **Combine with implicit signals**
   ```python
   # Hybrid scoring (recommended)
   final_score = 0.3 * onnx_score + 0.4 * access_count + 0.3 * recency
   ```

3. **Manual validation for important decisions**
   ```bash
   # Review low-scoring memories before archival
   analyze_quality_distribution()  # Check bottom 10 manually
   ```

#### Mid-Term (1-2 Weeks)

4. **Implement hybrid quality scoring** (Issue #268)
   - Combine ONNX + access patterns + recency + completeness
   - Reduces reliance on single model

5. **Add user feedback system** (Issue #268)
   - Allow manual ratings (👍/👎)
   - Weight user ratings 2-3x higher than AI scores

#### Long-Term (1-3 Months)

6. **Evaluate LLM-as-judge** (Issue #268)
   - Use Groq/Gemini for absolute quality assessment
   - ONNX only for relative ranking

7. **Improve query generation** (Issue #268)
   - Extract diverse queries from content (not just tags)
   - Reduces self-matching bias

### Performance Impact (Measured)

**A/B Test Results** (5 test queries, v8.48.3):
- Standard search: 38.2ms average
- Quality boost (0.3): 44.7ms average (+17% overhead)
- Quality boost (0.5): 45.7ms average (+20% overhead)

**Quality improvement**: Minimal (0-3% ranking changes) when top results already high-quality.

**Recommendation**: Use quality boost **only** for:
- Large databases (>10,000 memories)
- Explicit "best practices" or "authoritative" searches
- When quality variance is high

### Local SLM (Tier 1 - Primary)

**Model**: `ms-marco-MiniLM-L-6-v2` (23MB)
**Architecture**: Cross-encoder (processes query + memory together)
**Performance**:
- CPU: 50-100ms per evaluation
- GPU (CUDA/MPS/DirectML): 10-20ms per evaluation

**Scoring Process**:
1. Tokenize: `[CLS] query [SEP] memory [SEP]`
2. Run ONNX inference (local, private)
3. Return relevance score 0.0-1.0

**GPU Acceleration** (automatic):
- CUDA (NVIDIA)
- CoreML/MPS (Apple Silicon)
- DirectML (Windows)
- CPU fallback (always works)

## Installation & Setup

### 1. Basic Setup (Local SLM Only)

**Zero configuration required** - The quality system works out of the box with local SLM:

```bash
# Install MCP Memory Service (if not already installed)
pip install mcp-memory-service

# Quality system is enabled by default with local SLM
# No API keys needed, no external calls
```

### 2. Optional: Cloud APIs (Opt-In)

If you want cloud-based scoring (Groq or Gemini):

```bash
# Enable Groq API (fast, cheap)
export GROQ_API_KEY="your-groq-api-key"
export MCP_QUALITY_AI_PROVIDER=groq  # or "auto" to try all tiers

# Enable Gemini API (Google)
export GOOGLE_API_KEY="your-gemini-api-key"
export MCP_QUALITY_AI_PROVIDER=gemini
```

### 3. Configuration Options

```bash
# Quality System Core
export MCP_QUALITY_SYSTEM_ENABLED=true         # Default: true
export MCP_QUALITY_AI_PROVIDER=local           # local|groq|gemini|auto|none

# Local SLM Configuration (Tier 1)
export MCP_QUALITY_LOCAL_MODEL=ms-marco-MiniLM-L-6-v2  # Model name
export MCP_QUALITY_LOCAL_DEVICE=auto           # auto|cpu|cuda|mps|directml

# Quality-Boosted Search (Opt-In)
export MCP_QUALITY_BOOST_ENABLED=false         # Default: false (opt-in)
export MCP_QUALITY_BOOST_WEIGHT=0.3            # 0.0-1.0 (30% quality, 70% semantic)

# Quality-Based Retention (Consolidation)
export MCP_QUALITY_RETENTION_HIGH=365          # Days for quality ≥0.7
export MCP_QUALITY_RETENTION_MEDIUM=180        # Days for quality 0.5-0.7
export MCP_QUALITY_RETENTION_LOW_MIN=30        # Min days for quality <0.5
export MCP_QUALITY_RETENTION_LOW_MAX=90        # Max days for quality <0.5
```

## Using the Quality System

### 1. Automatic Quality Scoring

Quality scores are calculated automatically when memories are retrieved:

```bash
# Normal retrieval - quality scoring happens in background
claude /memory-recall "what did I work on yesterday"

# Quality score is updated in metadata (non-blocking)
```

### 2. Manual Rating (Optional)

Override AI scores with manual ratings:

```bash
# Rate a memory (MCP tool)
rate_memory(
    content_hash="abc123...",
    rating=1,  # -1 (bad), 0 (neutral), 1 (good)
    feedback="This was very helpful!"
)

# Manual ratings weighted 60%, AI scores weighted 40%
```

**HTTP API**:
```bash
curl -X POST http://127.0.0.1:8000/api/quality/memories/{hash}/rate \
  -H "Content-Type: application/json" \
  -d '{"rating": 1, "feedback": "Helpful!"}'
```

### 3. Quality-Boosted Search

Enable quality-based reranking for better results:

**Method 1: Global Configuration**
```bash
export MCP_QUALITY_BOOST_ENABLED=true
claude /memory-recall "search query"  # Uses quality boost
```

**Method 2: Per-Query (MCP Tool)**
```bash
# Search with quality boost (MCP tool)
retrieve_with_quality_boost(
    query="search query",
    n_results=10,
    quality_weight=0.3  # 30% quality, 70% semantic
)
```

**Algorithm**:
1. Over-fetch 3× candidates (30 results for top 10)
2. Rerank by: `0.7 × semantic_similarity + 0.3 × quality_score`
3. Return top N results

**Performance**: <100ms total (50ms semantic search + 20ms reranking + 30ms quality scoring)

### 4. View Quality Metrics

**MCP Tool**:
```bash
get_memory_quality(content_hash="abc123...")

# Returns:
# - quality_score: Current composite score (0.0-1.0)
# - quality_provider: Which tier scored it (ONNXRankerModel, etc.)
# - access_count: Number of retrievals
# - last_accessed_at: Last access timestamp
# - ai_scores: Historical AI evaluation scores
# - user_rating: Manual rating if present
```

**HTTP API**:
```bash
curl http://127.0.0.1:8000/api/quality/memories/{hash}
```

### 5. Quality Analytics

**MCP Tool**:
```bash
analyze_quality_distribution(min_quality=0.0, max_quality=1.0)

# Returns:
# - total_memories: Total count
# - high_quality_count: Score ≥0.7
# - medium_quality_count: 0.5 ≤ score < 0.7
# - low_quality_count: Score < 0.5
# - average_score: Mean quality score
# - provider_breakdown: Count by provider
# - top_10_memories: Highest scoring
# - bottom_10_memories: Lowest scoring
```

**Dashboard** (http://127.0.0.1:8000/):
- Quality badges on all memory cards (color-coded by tier)
- Analytics view with distribution charts
- Provider breakdown pie chart
- Top/bottom performers lists

## Quality-Based Memory Management

### 1. Quality-Based Forgetting (Consolidation)

High-quality memories are preserved longer during consolidation:

| Quality Tier | Score Range | Retention Period |
|--------------|-------------|------------------|
| **High** | ≥0.7 | 365 days inactive |
| **Medium** | 0.5-0.7 | 180 days inactive |
| **Low** | <0.5 | 30-90 days inactive (scaled by score) |

**How it works**:
- Weekly consolidation scans inactive memories
- Applies quality-based thresholds
- Archives low-quality memories sooner
- Preserves high-quality memories longer

### 2. Quality-Weighted Decay

High-quality memories decay slower in relevance scoring:

```
decay_multiplier = 1.0 + (quality_score × 0.5)
# High quality (0.9): 1.45× multiplier
# Medium quality (0.5): 1.25× multiplier
# Low quality (0.2): 1.10× multiplier

final_relevance = base_relevance × decay_multiplier
```

**Effect**: High-quality memories stay relevant longer in search results.

## Privacy & Cost

### Privacy Modes

| Mode | Configuration | Privacy | Cost |
|------|---------------|---------|------|
| **Local Only** | `MCP_QUALITY_AI_PROVIDER=local` | ✅ Full (no external calls) | $0 |
| **Hybrid** | `MCP_QUALITY_AI_PROVIDER=auto` | ⚠️ Cloud fallback | ~$0.30/mo |
| **Cloud** | `MCP_QUALITY_AI_PROVIDER=groq` | ❌ External API | ~$0.30/mo |
| **Implicit Only** | `MCP_QUALITY_AI_PROVIDER=none` | ✅ Full (no AI) | $0 |

### Cost Comparison (3500 memories, 100 retrievals/day)

| Provider | Monthly Cost | Notes |
|----------|--------------|-------|
| **Local SLM** | **$0** | Free forever, runs locally |
| Groq (Kimi K2) | ~$0.30-0.50 | Fast, good quality |
| Gemini Flash | ~$0.40-0.60 | Slower, free tier available |
| Implicit Only | $0 | No AI scoring, usage patterns only |

**Recommendation**: Use default local SLM (zero cost, full privacy, fast).

## Performance Benchmarks

| Operation | Latency | Notes |
|-----------|---------|-------|
| **Local SLM Scoring (CPU)** | 50-100ms | Per memory evaluation |
| **Local SLM Scoring (GPU)** | 10-20ms | With CUDA/MPS/DirectML |
| **Quality-Boosted Search** | <100ms | Over-fetch + rerank |
| **Implicit Signals** | <10ms | Always fast |
| **Quality Metadata Update** | <5ms | Storage backend write |

**Target Metrics**:
- Quality calculation overhead: <10ms
- Search latency with boost: <100ms total
- No user-facing blocking (async scoring)

## Troubleshooting

### Local SLM Not Working

**Symptom**: `quality_provider: ImplicitSignalsEvaluator` (should be `ONNXRankerModel`)

**Fixes**:
1. Check ONNX Runtime installed:
   ```bash
   pip install onnxruntime
   ```

2. Check model downloaded:
   ```bash
   ls ~/.cache/mcp_memory/onnx_models/ms-marco-MiniLM-L-6-v2/
   # Should contain: model.onnx, tokenizer.json
   ```

3. Check logs for errors:
   ```bash
   tail -f logs/mcp_memory_service.log | grep quality
   ```

### Quality Scores Always 0.5

**Symptom**: All memories have `quality_score: 0.5` (neutral default)

**Cause**: Quality scoring not triggered yet (memories haven't been retrieved)

**Fix**: Retrieve memories to trigger scoring:
```bash
claude /memory-recall "any search query"
# Quality scoring happens in background after retrieval
```

### GPU Not Detected

**Symptom**: Local SLM uses CPU despite having GPU

**Fixes**:
1. Install GPU-enabled ONNX Runtime:
   ```bash
   # NVIDIA CUDA
   pip install onnxruntime-gpu

   # DirectML (Windows)
   pip install onnxruntime-directml
   ```

2. Force device selection:
   ```bash
   export MCP_QUALITY_LOCAL_DEVICE=cuda  # or mps, directml
   ```

### Quality Boost Not Working

**Symptom**: Search results don't show quality reranking

**Checks**:
1. Verify enabled:
   ```bash
   echo $MCP_QUALITY_BOOST_ENABLED  # Should be "true"
   ```

2. Use explicit MCP tool:
   ```bash
   retrieve_with_quality_boost(query="test", quality_weight=0.5)
   ```

3. Check debug info in results:
   ```python
   result.debug_info['reranked']  # Should be True
   result.debug_info['quality_score']  # Should exist
   ```

## Best Practices

### 1. Start with Defaults (Updated for v8.48.3)

Use local SLM (default) for:
- Zero cost
- Full privacy
- Offline capability
- **Good for relative ranking** (not absolute quality assessment)

**Important**: Local SLM scores should be **combined with implicit signals** (access patterns, recency) for best results. Do not rely on ONNX scores alone.

### 2. Enable Quality Boost Gradually

```bash
# Week 1: Collect quality scores (boost disabled)
export MCP_QUALITY_BOOST_ENABLED=false

# Week 2: Test with low weight
export MCP_QUALITY_BOOST_ENABLED=true
export MCP_QUALITY_BOOST_WEIGHT=0.2  # 20% quality

# Week 3+: Increase if helpful
export MCP_QUALITY_BOOST_WEIGHT=0.3  # 30% quality (recommended)
```

### 3. Monitor Quality Distribution (With Caution)

Check analytics regularly, but interpret with awareness of limitations:
```bash
analyze_quality_distribution()

# Current observed distribution (v8.48.3):
# - High quality (≥0.7): 32.2% (includes ~25% false positives from self-matching)
# - Medium quality (0.5-0.7): 27.4%
# - Low quality (<0.5): 40.4%

# Ideal distribution (future with hybrid scoring):
# - High quality (≥0.7): 20-30% of memories
# - Medium quality (0.5-0.7): 50-60%
# - Low quality (<0.5): 10-20%
```

**Warning**: High scores may not always indicate high quality due to self-matching bias. Validate manually before making retention decisions.

### 4. Manual Rating for Edge Cases

Rate important memories manually:
```bash
# After finding a very helpful memory
rate_memory(content_hash="abc123...", rating=1, feedback="Critical info!")

# After finding unhelpful memory
rate_memory(content_hash="def456...", rating=-1, feedback="Outdated")
```

Manual ratings weighted 60%, AI scores 40%.

### 5. Periodic Review (Updated for v8.48.3)

Monthly checklist:
- [ ] Check quality distribution (analytics dashboard)
- [ ] **Manually validate** top 10 performers (verify genuinely helpful, not just self-matching bias)
- [ ] **Manually validate** bottom 10 before deletion (may be low-quality or just poor matches)
- [ ] Verify provider breakdown (target: 75%+ local SLM)
- [ ] Check average quality score (current: 0.469, target with hybrid: 0.6+)
- [ ] **Review Issue #268** progress on quality improvements

## Advanced Configuration

### Custom Retention Policy

```bash
# Conservative: Preserve longer
export MCP_QUALITY_RETENTION_HIGH=730       # 2 years for high quality
export MCP_QUALITY_RETENTION_MEDIUM=365     # 1 year for medium
export MCP_QUALITY_RETENTION_LOW_MIN=90     # 90 days minimum for low

# Aggressive: Archive sooner
export MCP_QUALITY_RETENTION_HIGH=180       # 6 months for high
export MCP_QUALITY_RETENTION_MEDIUM=90      # 3 months for medium
export MCP_QUALITY_RETENTION_LOW_MIN=14     # 2 weeks minimum for low
```

### Custom Quality Boost Weight

```bash
# Semantic-first (default)
export MCP_QUALITY_BOOST_WEIGHT=0.3  # 30% quality, 70% semantic

# Balanced
export MCP_QUALITY_BOOST_WEIGHT=0.5  # 50% quality, 50% semantic

# Quality-first
export MCP_QUALITY_BOOST_WEIGHT=0.7  # 70% quality, 30% semantic
```

**Recommendation**: Start with 0.3, increase if quality boost improves results.

### Hybrid Cloud Strategy

Use local SLM primarily, cloud APIs as fallback:

```bash
export MCP_QUALITY_AI_PROVIDER=auto  # Try all available tiers
export GROQ_API_KEY="your-key"       # Groq as Tier 2 fallback
```

**Behavior**:
1. Try local SLM (99% success rate)
2. If fails, try Groq API
3. If fails, try Gemini API
4. Ultimate fallback: Implicit signals only

## Success Metrics (Phase 1 Targets)

From Issue #260 and #261 roadmap:

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Retrieval Precision** | >70% useful (top-5) | Up from ~50% baseline |
| **Quality Coverage** | >30% memories scored | Within 3 months |
| **Quality Distribution** | 20-30% high-quality | Pareto principle |
| **Search Latency** | <100ms with boost | SQLite-vec backend |
| **Monthly Cost** | <$0.50 or $0 | Groq API or local SLM |
| **Local SLM Usage** | >95% of scoring | Tier 1 success rate |

## FAQ

### Q: Do I need API keys for the quality system?

**A**: No! The default local SLM works with zero configuration, no API keys, and no external calls.

### Q: How much does it cost?

**A**: $0 with the default local SLM. Optional cloud APIs cost ~$0.30-0.50/month for typical usage.

### Q: Does quality scoring slow down searches?

**A**: No. Scoring happens asynchronously in the background. Quality-boosted search adds <20ms overhead.

### Q: Can I disable the quality system?

**A**: Yes, set `MCP_QUALITY_SYSTEM_ENABLED=false`. System works normally without quality scores.

### Q: How accurate is the local SLM?

**A**: 80%+ correlation with human quality ratings. Good enough for ranking and retention decisions.

### Q: What if the local SLM fails to download?

**A**: System falls back to implicit signals (access patterns). No failures, degraded gracefully.

### Q: Can I use my own quality scoring model?

**A**: Yes! Implement the `QualityEvaluator` interface and configure via `MCP_QUALITY_AI_PROVIDER`.

### Q: Does this work offline?

**A**: Yes! Local SLM works fully offline. No internet required for quality scoring.

## Related Documentation

- [Issue #260](https://github.com/doobidoo/mcp-memory-service/issues/260) - Quality System Specification
- [Issue #261](https://github.com/doobidoo/mcp-memory-service/issues/261) - Roadmap (Quality → Agentic RAG)
- [Consolidation Guide](./memory-consolidation-guide.md) - Detailed consolidation documentation
- [API Reference](../api/quality-endpoints.md) - HTTP API documentation

## Changelog

**v8.48.3** (2025-12-08):
- **Documentation Update**: Added comprehensive ONNX limitations section
- Documented self-matching bias and bimodal distribution issues
- Updated best practices with manual validation recommendations
- Added performance benchmarks from evaluation (4,762 memories)
- Linked to [Quality System Evaluation Report](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Quality-System-Evaluation)
- Created [Issue #268](https://github.com/doobidoo/mcp-memory-service/issues/268) for Phase 2 improvements

**v8.45.0** (2025-01-XX):
- Initial release of Memory Quality System
- Local SLM (ONNX) as primary tier
- Quality-based forgetting in consolidation
- Quality-boosted search with reranking
- Dashboard UI with quality badges and analytics
- Comprehensive MCP tools and HTTP API

---

**Need help?** Open an issue at https://github.com/doobidoo/mcp-memory-service/issues

**Quality System Improvements**: See [Issue #268](https://github.com/doobidoo/mcp-memory-service/issues/268) for planned enhancements
