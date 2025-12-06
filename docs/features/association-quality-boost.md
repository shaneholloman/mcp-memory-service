# Association-Based Quality Boost (v8.47.0+)

## Overview

The Association-Based Quality Boost feature enhances memory quality scores based on connection patterns during consolidation. Memories with many connections to other memories receive a quality boost, leveraging the network effect principle: well-connected memories are likely more valuable.

## How It Works

### Core Concept

When consolidation runs, memories with high connection counts (≥5 by default) receive a quality score boost. This is based on the assumption that:

1. **Network Effect**: Memories frequently referenced by other memories are likely important
2. **Context Validation**: Many connections suggest the memory provides useful context
3. **Knowledge Hubs**: Well-connected memories serve as knowledge anchors

### Quality Boost Calculation

```python
if connection_count >= MIN_CONNECTIONS_FOR_BOOST:
    boosted_quality = min(1.0, quality_score * QUALITY_BOOST_FACTOR)
```

**Default Values:**
- `MIN_CONNECTIONS_FOR_BOOST`: 5 connections
- `QUALITY_BOOST_FACTOR`: 1.2 (20% boost)
- Quality scores are capped at 1.0

## Configuration

### Environment Variables

```bash
# Enable association-based quality boost (default: true)
export MCP_CONSOLIDATION_QUALITY_BOOST_ENABLED=true

# Minimum connections required for boost (default: 5)
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=5

# Quality boost multiplier (default: 1.2 = 20% boost)
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.2

# Valid range: 1.0-2.0
# Examples:
#   1.1 = 10% boost (conservative)
#   1.2 = 20% boost (default)
#   1.5 = 50% boost (aggressive)
```

### Tuning Guidelines

**Conservative (Research/Academic):**
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=10
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.1
```

**Balanced (Default):**
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=5
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.2
```

**Aggressive (Knowledge Graph):**
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=3
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.3
```

## Impact on Memory Lifecycle

### 1. **Relevance Calculation**

Association-boosted quality scores affect the relevance score used in consolidation:

```
relevance = base_importance * decay_factor * connection_boost * access_boost * quality_multiplier

quality_multiplier = 1.0 + (quality_score * 0.5)  # 1.0-1.5x range
```

**Example:**
- Original quality: 0.5 → multiplier: 1.25
- After 20% boost: 0.6 → multiplier: 1.3
- **Net effect**: 4% increase in total relevance

### 2. **Retention Policy**

Quality-based retention thresholds (v8.45.0+):

| Quality Range | Retention | Example Boost Impact |
|---------------|-----------|----------------------|
| **High (≥0.7)** | 365 days | 0.6 → 0.72 crosses threshold |
| **Medium (0.5-0.7)** | 180 days | 0.48 → 0.58 crosses threshold |
| **Low (<0.5)** | 30-90 days | 0.4 → 0.48 stays low |

**Key Insight**: A 20% quality boost can move memories from "medium retention" to "high retention" tier.

### 3. **Forgetting Resistance**

The boost helps memories resist archival:

```python
# Quality-based forgetting threshold calculation
days_inactive = (current_time - last_accessed).days

if quality_score >= 0.7:
    threshold_days = 365  # High quality
elif quality_score >= 0.5:
    threshold_days = 180  # Medium quality
else:
    threshold_days = 30 + (quality_score / 0.5) * 60  # Low quality (30-90 days)

if days_inactive > threshold_days:
    archive(memory)
```

## Persistence

Boosted quality scores are persisted to memory metadata:

```python
{
    "quality_score": 0.72,  # Boosted value
    "quality_boost_applied": true,
    "quality_boost_date": "2025-12-06T10:30:00Z",
    "quality_boost_reason": "association_connections",
    "quality_boost_connection_count": 8,
    "original_quality_before_boost": 0.6
}
```

This metadata allows:
- **Audit trail**: Track which memories received boosts and why
- **Reversibility**: Original scores preserved for analysis
- **Analytics**: Monitor boost effectiveness over time

## Monitoring

### Consolidation Logs

Debug-level logging for each boost:

```
Association quality boost: a1b2c3d4e5f6 quality 0.500 → 0.600 (8 connections)
```

Info-level logging when persisting:

```
Persisting association quality boost for a1b2c3d4e5f6: 0.600 → 0.720
```

### Quality Distribution Analysis

Check boost impact with:

```bash
curl http://127.0.0.1:8000/api/quality/distribution
```

Look for:
- Increased high-quality memory count (≥0.7)
- Decreased low-quality memory count (<0.5)
- Distribution shift toward higher scores

## Use Cases

### 1. **Knowledge Graph Enhancement**

**Scenario**: Building a personal knowledge base with interconnected notes.

**Configuration**:
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=3
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.3
```

**Benefit**: Core concepts with many connections get boosted, forming knowledge anchors.

### 2. **Code Documentation**

**Scenario**: Storing code snippets, API references, and implementation notes.

**Configuration**:
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=5
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.2
```

**Benefit**: Frequently referenced utilities and patterns get higher retention.

### 3. **Research Notes**

**Scenario**: Academic research with cited sources and cross-references.

**Configuration**:
```bash
export MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST=10
export MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR=1.1
```

**Benefit**: Well-cited sources get conservative boost, preventing over-promotion.

## Performance Impact

### Computational Cost

**Negligible** - Quality boost adds:
- ~5-10 microseconds per memory during consolidation
- Single hash lookup + arithmetic operation
- No database queries or external API calls

### Memory Overhead

**Minimal** - Adds ~200 bytes per boosted memory:
- 5 metadata fields × ~40 bytes each

### Consolidation Time

**No measurable impact** on consolidation duration:
- SQLite-Vec: Still ~5-25s
- Hybrid: Still ~4-6min (dominated by cloud sync)

## Limitations

### 1. **Connection Quality Blind**

Current implementation boosts quality based on connection **count**, not connection **quality**.

**Example Issue**:
- Memory A: 10 connections to low-quality memories
- Memory B: 4 connections to high-quality memories
- Result: A gets boosted, B doesn't (despite likely being more valuable)

**Future Enhancement**: Track connected memory quality (see `MCP_CONSOLIDATION_MIN_CONNECTED_QUALITY` config variable for future use).

### 2. **No Decay of Boosts**

Once boosted, quality scores persist indefinitely (unless manually reset).

**Example Issue**: A previously popular memory loses relevance but retains boost.

**Workaround**: Periodic quality re-evaluation could detect this.

### 3. **Bootstrap Problem**

New memories start with few connections, even if high quality.

**Mitigation**: Initial quality scoring (ONNX/LLM) provides baseline before boost.

## Future Enhancements

### Phase 2: Connection Quality Analysis

```python
# Proposed enhancement
connected_memories = get_connected_memories(memory_hash)
avg_connected_quality = mean([m.quality_score for m in connected_memories])

if avg_connected_quality >= MIN_CONNECTED_QUALITY:  # e.g., 0.7
    apply_quality_boost(memory)
```

### Phase 3: Temporal Decay

```python
# Boost degrades over time if connections don't persist
boost_age_days = days_since(quality_boost_date)
if boost_age_days > 90 and current_connection_count < original_count * 0.5:
    reduce_quality_boost(memory)
```

### Phase 4: Bidirectional Boost

```python
# High-quality memories boost connected memories
if quality_score >= 0.8:
    for connected_memory in get_connections(memory_hash):
        if connected_memory.quality_score < 0.6:
            apply_minor_boost(connected_memory)  # e.g., 5% boost
```

## Troubleshooting

### Issue: Boosts Not Being Applied

**Symptoms**: Logs show no "Association quality boost" messages during consolidation.

**Checks**:
1. Verify feature is enabled: `echo $MCP_CONSOLIDATION_QUALITY_BOOST_ENABLED`
2. Check connection counts: Most memories may have <5 connections
3. Review logs: `grep "Association quality" ~/.mcp-memory/logs/consolidation.log`

**Solution**: Lower threshold or wait for more connections to form.

### Issue: Too Many Low-Quality Memories Boosted

**Symptoms**: Quality distribution shows unexpected high scores.

**Checks**:
1. Review boost factor: `echo $MCP_CONSOLIDATION_QUALITY_BOOST_FACTOR`
2. Check minimum connections: `echo $MCP_CONSOLIDATION_MIN_CONNECTIONS_FOR_BOOST`

**Solution**: Increase min connections or decrease boost factor.

### Issue: Important Memories Not Getting Boost

**Symptoms**: High-quality content with moderate connections not boosted.

**Checks**:
1. Connection count threshold too high
2. Associations not being discovered (check association discovery settings)

**Solution**: Lower threshold or increase association discovery frequency.

## Testing

Run association quality boost tests:

```bash
pytest tests/consolidation/test_decay.py -k "association" -v
```

**Test Coverage**:
- ✅ Quality boost increases scores
- ✅ Threshold enforcement (min connections)
- ✅ Quality cap at 1.0
- ✅ Feature can be disabled
- ✅ Boosts persist to memory metadata

## Related Documentation

- [Memory Quality System Guide](../guides/memory-quality-guide.md)
- [Memory Consolidation Guide](../guides/memory-consolidation-guide.md)
- [Quality-Based Retention Policy](../quality-retention.md)
- [Association Discovery](../consolidation/associations.md)

## Version History

- **v8.47.0**: Initial implementation
  - Basic connection-count-based quality boost
  - Configurable via environment variables
  - Metadata persistence
  - Comprehensive test coverage
