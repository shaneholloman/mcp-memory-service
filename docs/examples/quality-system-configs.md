# Memory Quality System - Example Configurations

> **Version**: 8.49.0
> **Updated**: December 8, 2025
> **See Also**: [Memory Quality Guide](../guides/memory-quality-guide.md), [Evaluation Report](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Quality-System-Evaluation)

This document provides tested configuration examples for different use cases. **v8.49.0 introduces NVIDIA DeBERTa quality classifier** as the new default model, eliminating self-matching bias and providing absolute quality assessment.

---

## Configuration 1: Default (Recommended for Most Users - v8.49.0+)

**Use case**: General usage with accurate quality assessment

```bash
# .env configuration (v8.49.0+ defaults)
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local                               # Local ONNX only
MCP_QUALITY_LOCAL_MODEL=nvidia-quality-classifier-deberta   # DeBERTa (default)
MCP_QUALITY_BOOST_ENABLED=true                              # Recommended with DeBERTa
MCP_QUALITY_BOOST_WEIGHT=0.3                                # 30% quality, 70% semantic

# Benefits over v8.48.x (MS-MARCO):
# ✅ No self-matching bias
# ✅ Absolute quality assessment (query-independent)
# ✅ Uniform distribution (mean: 0.60-0.70)
# ✅ Fewer false positives (<5% perfect scores)
```

**Why this works**:
- Zero cost, full privacy (runs locally)
- Accurate absolute quality assessment
- Suitable for archival and retention decisions
- GPU acceleration for fast inference (20-40ms)

**When to use**:
- ✅ **All new installations** (default)
- ✅ **All database sizes** (small to large)
- ✅ **Cost-conscious users** (zero API costs)
- ✅ **Privacy-focused setups** (no external calls)

---

## Configuration 2: Quality-Boosted (Large Databases)

**Use case**: Large memory databases where quality variance is high

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local
MCP_QUALITY_BOOST_ENABLED=true          # Enable quality boost
MCP_QUALITY_BOOST_WEIGHT=0.3            # 30% quality, 70% semantic

# Note: Only provides 0-3% ranking improvement in v8.48.3
# Most beneficial when:
# - Database has >10,000 memories
# - Quality variance is high
# - Searching for "best practices" or "authoritative" content
```

**Why this works**:
- Minimal latency impact (+17%, 6.5ms)
- Still zero cost with local ONNX
- Small but measurable improvement in large databases

**When to use**:
- >10,000 memories
- Diverse quality levels
- Research or documentation heavy usage

---

## Configuration 3: Privacy-First (No AI Scoring)

**Use case**: Maximum privacy, implicit signals only

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=none            # Disable all AI scoring
# No ONNX model download, no API calls

# Quality scores based purely on:
# - Access frequency (40%)
# - Recency (30%)
# - Retrieval ranking (30%)
```

**Why this works**:
- No AI models, no external calls
- Still benefits from usage patterns
- Zero overhead (implicit signals are fast)

**When to use**:
- Air-gapped environments
- Strict privacy requirements
- Resource-constrained systems

---

## Configuration 4: Hybrid Strategy (Phase 2 - Coming Soon)

**Use case**: Combine ONNX + implicit signals for better scores

```bash
# Future configuration (Issue #268)
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local
MCP_QUALITY_HYBRID_ENABLED=true         # Enable hybrid scoring

# Hybrid formula (proposed):
# quality = 0.30*onnx + 0.25*access + 0.20*recency + 0.15*tags + 0.10*completeness
```

**Why this will work better**:
- Reduces reliance on single model (ONNX)
- Incorporates actual usage patterns
- Mitigates self-matching bias

**Status**: Planned for Phase 2 (1-2 weeks)

---

## Configuration 5: Cloud-Enhanced (Opt-In)

**Use case**: Users who want better quality assessment and don't mind API costs

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=auto            # Try all tiers
GROQ_API_KEY="your-groq-api-key"        # Groq as Tier 2

# Behavior:
# 1. Try local ONNX (99% success rate)
# 2. Fallback to Groq API if needed
# 3. Ultimate fallback: Implicit signals

# Cost: ~$0.30-0.50/month for typical usage
```

**Why this works**:
- Local-first, cloud as fallback
- Better quality assessment with Groq
- Still privacy-preserving (API calls are opt-in)

**When to use**:
- Professional/commercial usage
- Budget for cloud APIs (~$0.50/month)
- Want better quality assessment

---

## Configuration 6: LLM-as-Judge (Phase 3 - Coming Soon)

**Use case**: Absolute quality assessment for high-value memories

```bash
# Future configuration (Issue #268)
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=llm_judge       # LLM-as-judge mode
GROQ_API_KEY="your-groq-api-key"        # Use Groq for quality

# LLM evaluates memories with structured prompts:
# - Specificity: Is it detailed and actionable?
# - Accuracy: Is the information correct?
# - Completeness: Does it cover the topic fully?
# - Relevance: Is it still current/applicable?

# Cost: ~$0.05-0.10 per 1,000 memories (batch evaluation)
```

**Why this will work better**:
- LLM understands context and nuance
- Absolute quality assessment (not just relevance)
- No self-matching bias

**Status**: Planned for Phase 3 (1-3 months)

---

## Configuration 7: Conservative Retention (Preserve More)

**Use case**: Never want to lose potentially valuable memories

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local

# Conservative retention periods
MCP_QUALITY_RETENTION_HIGH=730          # 2 years for high quality
MCP_QUALITY_RETENTION_MEDIUM=365        # 1 year for medium
MCP_QUALITY_RETENTION_LOW_MIN=180       # 6 months minimum for low

# Warning: Given self-matching bias, be extra conservative
# Many "low quality" memories may be false negatives
```

**Why this works**:
- Accounts for potential scoring bias
- Preserves memories longer
- Safer with uncertain quality scores

**When to use**:
- Critical knowledge bases
- Archival/research projects
- When in doubt, preserve

---

## Configuration 8: Aggressive Cleanup (Minimize Storage)

**Use case**: Want to keep only highest quality memories

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local

# Aggressive retention periods
MCP_QUALITY_RETENTION_HIGH=180          # 6 months for high
MCP_QUALITY_RETENTION_MEDIUM=90         # 3 months for medium
MCP_QUALITY_RETENTION_LOW_MIN=30        # 1 month minimum for low

# ⚠️ DANGER: Given self-matching bias, this may delete valuable memories
# Recommendation: Manually review candidates before archival
# See: analyze_quality_distribution() -> Review bottom 10
```

**Why this is risky**:
- May archive genuinely useful memories (false negatives)
- ONNX scores not validated for absolute quality
- No user feedback to verify

**When to use**:
- Storage-constrained environments
- Ephemeral/temporary knowledge
- **ONLY after manual validation**

---

## Configuration 9: DeBERTa Quality Classifier (Recommended - v8.49.0+)

**Use case**: Absolute quality assessment without self-matching bias

```bash
# .env configuration
MCP_QUALITY_SYSTEM_ENABLED=true
MCP_QUALITY_AI_PROVIDER=local
MCP_QUALITY_LOCAL_MODEL=nvidia-quality-classifier-deberta  # Default v8.49.0+
MCP_QUALITY_LOCAL_DEVICE=auto                             # Auto-detect GPU

# Quality boost recommended with DeBERTa (more accurate scores)
MCP_QUALITY_BOOST_ENABLED=true
MCP_QUALITY_BOOST_WEIGHT=0.3

# Expected improvements:
# - Mean score: 0.60-0.70 (vs 0.469 with MS-MARCO)
# - Perfect 1.0 scores: <5% (vs 20% with MS-MARCO)
# - Uniform distribution (vs bimodal clustering)
# - No self-matching bias
```

**Why this works best**:
- ✅ **Eliminates self-matching bias** - Query-independent evaluation
- ✅ **Absolute quality assessment** - Designed for quality scoring
- ✅ **Uniform distribution** - More realistic score spread
- ✅ **Fewer false positives** - <5% perfect scores
- ✅ **Still zero cost** - Runs locally with GPU acceleration

**Performance**:
- Model size: 450MB (one-time download)
- CPU: 80-150ms per evaluation
- GPU (CUDA/MPS/DirectML): 20-40ms per evaluation
- ~20% slower than MS-MARCO but significantly more accurate

**Migration from MS-MARCO**:
```bash
# Export DeBERTa model (one-time)
python scripts/quality/export_deberta_onnx.py

# Re-evaluate existing memories
python scripts/quality/migrate_to_deberta.py

# Verify improved distribution
curl -ks https://127.0.0.1:8000/api/quality/distribution | python3 -m json.tool
```

**When to use**:
- ✅ **All new installations** (default in v8.49.0+)
- ✅ **Upgrading from v8.48.x** (migration script available)
- ✅ **When quality accuracy matters** (archival decisions, retention policies)
- ✅ **Large databases** (>5,000 memories)

**When NOT to use**:
- Extremely limited disk space (<500MB available)
- Legacy systems requiring MS-MARCO compatibility
- When 450MB model download is not feasible

**Fallback to MS-MARCO** (not recommended):
```bash
# Override to legacy model (only if needed)
export MCP_QUALITY_LOCAL_MODEL=ms-marco-MiniLM-L-6-v2
```

---

## Monitoring & Validation

Regardless of configuration, **always validate** quality scores before making decisions:

### 1. Weekly Check

```bash
# Run analytics
analyze_quality_distribution()

# Expected output (v8.48.3):
# - High (≥0.7): 32.2% (includes ~25% false positives)
# - Medium (0.5-0.7): 27.4%
# - Low (<0.5): 40.4%
```

### 2. Monthly Review

```bash
# 1. Check top performers (verify genuinely helpful)
analyze_quality_distribution() | grep "Top 10"

# 2. Check bottom performers (candidates for archival)
analyze_quality_distribution() | grep "Bottom 10"

# 3. Manually validate before deleting
rate_memory(content_hash="...", rating=-1, feedback="Actually useful, ONNX scored wrong")
```

### 3. Quarterly Audit

```bash
# Sample random memories across quality tiers
# Manually rate them
# Compare AI scores vs human ratings

# Track correlation:
# - Target: >0.7 correlation
# - Current (v8.48.3): ~0.5-0.6 (due to self-matching bias)
```

---

## Migration Path

### From v8.45.0 to v8.48.3 (Current)

**Changes**:
- Added ONNX limitations documentation
- Updated best practices with manual validation
- Kept quality boost as opt-in (good default)

**Action required**: None (backward compatible)

**Recommendation**: Review [Evaluation Report](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Quality-System-Evaluation)

### To Phase 2 (Hybrid Scoring)

**Planned changes** (Issue #268):
- Hybrid quality scoring (ONNX + implicit signals)
- User feedback system (manual ratings)
- A/B test framework

**Migration**:
```bash
# New config options
export MCP_QUALITY_HYBRID_ENABLED=true
export MCP_QUALITY_USER_FEEDBACK_ENABLED=true

# Existing scores will be recalculated with hybrid formula
```

### To Phase 3 (LLM-as-Judge)

**Planned changes** (Issue #268):
- LLM-based absolute quality assessment
- Quality-driven memory lifecycle
- Improved query generation

**Migration**:
```bash
# New config options
export MCP_QUALITY_AI_PROVIDER=llm_judge
export GROQ_API_KEY="your-key"

# Batch re-evaluation of existing memories (opt-in)
```

---

## Troubleshooting Common Issues

### Issue 1: All Memories Have Score 1.0

**Symptom**: Most memories have perfect quality scores

**Cause**: Self-matching bias from tag-generated queries

**Solution**:
```bash
# 1. Understand this is expected behavior (v8.48.3)
# 2. Use scores for relative ranking only
# 3. Combine with implicit signals
# 4. Wait for Phase 2 (hybrid scoring)
```

### Issue 2: Average Score Too Low (0.469)

**Symptom**: `analyze_quality_distribution()` shows avg 0.469

**Cause**: Bimodal distribution (many 1.0, many 0.0, few middle scores)

**Solution**:
```bash
# This is expected in v8.48.3
# Not a bug, but a model limitation
# Solutions coming in Phase 2/3 (Issue #268)
```

### Issue 3: Quality Boost Not Improving Results

**Symptom**: Enabling quality boost doesn't change ranking

**Cause**: Top results already high-quality (0-3% difference measured)

**Solution**:
```bash
# Keep boost disabled (default)
export MCP_QUALITY_BOOST_ENABLED=false

# Only enable for large databases or specific searches
retrieve_with_quality_boost(query="best practices", quality_weight=0.5)
```

---

## Best Practices Summary

**v8.49.0+ (DeBERTa)**:
1. **Use defaults** (Configuration 1 or 9) - DeBERTa provides accurate quality assessment
2. **Enable quality boost** - More effective with DeBERTa's accurate scores
3. **Trust quality scores** - Suitable for archival and retention decisions
4. **Monitor distribution monthly** with `analyze_quality_distribution()`
5. **Provide manual ratings** for important memories (enhances learning)
6. **Migrate from MS-MARCO** if upgrading: `python scripts/quality/migrate_to_deberta.py`

**v8.48.x and earlier (MS-MARCO)**:
1. **Upgrade to v8.49.0** for DeBERTa improvements
2. If staying on MS-MARCO: Use scores for **relative ranking only**
3. **Manually validate** before archival decisions (self-matching bias)
4. **Monitor false positives** (20% perfect 1.0 scores)

---

## Related Documentation

- [Memory Quality Guide](../guides/memory-quality-guide.md) - Comprehensive guide
- [Evaluation Report](https://github.com/doobidoo/mcp-memory-service/wiki/Memory-Quality-System-Evaluation) - Full analysis
- [Issue #268](https://github.com/doobidoo/mcp-memory-service/issues/268) - Planned improvements
- [CLAUDE.md](../../CLAUDE.md) - Quick reference

---

**Questions?** Open an issue at https://github.com/doobidoo/mcp-memory-service/issues
