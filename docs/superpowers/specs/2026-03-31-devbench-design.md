# DevBench — Practical Memory Retrieval Benchmark

**Date:** 2026-03-31
**Status:** Approved

---

## Goal

Benchmark mcp-memory-service retrieval quality using realistic developer workflow memories and queries derived from the project itself. Complements the academic LoCoMo benchmark with a practical, domain-specific evaluation.

## Why Not Just LoCoMo

LoCoMo tests fictional persona conversations with relative time references. mcp-memory-service stores developer learnings, decisions, bug fixes, architecture notes, and config knowledge. DevBench tests what actually matters for our users.

## Dataset

**Source:** mcp-memory-service project content (CHANGELOG, CLAUDE.md, Issues, PRs).

**File:** `scripts/benchmarks/devbench_dataset.json`

### 30 Memories across 5 types

| Type | Count | Tag Pattern | Example |
|------|-------|-------------|---------|
| `decision` | 6 | `bench:decision-N` | "Chose SQLite-Vec over FAISS — serverless, supports KNN" |
| `learning` | 6 | `bench:learning-N` | "Memory.metadata is for custom KV only — use direct attribute access for tags" |
| `bug-fix` | 6 | `bench:bugfix-N` | "Test cleanup deleted 8,663 production memories — triple safety in PR #438" |
| `architecture` | 6 | `bench:arch-N` | "Storage backends use Strategy Pattern — BaseStorage with 3 implementations" |
| `config` | 6 | `bench:config-N` | "journal_mode=WAL required for concurrent HTTP + MCP access" |

Each memory has:
- `content`: Realistic text derived from project docs
- `tags`: `["devbench", "bench:<type>-<N>"]` + relevant topic tags
- `memory_type`: One of the 5 types above
- `created_at`: Plausible timestamp

### 20 Queries in 4 categories

| Category | Count | Description | Expected Matches |
|----------|-------|-------------|-----------------|
| `exact` | 5 | Direct questions matching memory content closely | 1-2 memories each |
| `semantic` | 5 | Rephrased/indirect questions requiring semantic understanding | 1-2 memories each |
| `cross-type` | 5 | Questions matching memories across multiple types | 2-3 memories each |
| `negative` | 5 | Questions about topics not in the dataset | 0 memories |

Each query has:
- `question`: Natural language query
- `expected_tags`: List of `bench:*` tags that should appear in results (empty for negative)
- `category`: One of the 4 categories above

### JSON Format

```json
{
  "memories": [
    {
      "content": "Chose SQLite-Vec over FAISS for the storage backend because...",
      "tags": ["devbench", "bench:decision-1", "storage", "sqlite"],
      "memory_type": "decision",
      "created_at_iso": "2025-06-15T10:00:00Z"
    }
  ],
  "queries": [
    {
      "question": "Why did we choose SQLite-Vec?",
      "expected_tags": ["bench:decision-1"],
      "category": "exact"
    }
  ]
}
```

## Benchmark Script

**File:** `scripts/benchmarks/benchmark_devbench.py`

Reuses `locomo_evaluator.py` for metrics (Recall@K, Precision@K, MRR).

### Pipeline

1. Load `devbench_dataset.json`
2. Create isolated SQLite-Vec DB (temp directory)
3. Ingest all 30 memories with tags, memory_type, timestamps
4. For each query:
   - `storage.retrieve(query, n_results=K)`
   - Check if expected `bench:*` tags appear in retrieved memories' tags
   - Compute Recall@K, Precision@K, MRR
5. For negative queries: compute `false_positive_rate` (fraction of top-K with any `bench:*` tag)
6. Aggregate per category + overall

### Evidence Matching

Match by tag presence: a retrieved memory is "relevant" if its tags contain any of the query's `expected_tags`. Each expected tag gets a unique label for proper multi-evidence recall (same approach as LoCoMo fix).

### Ablation

Optional `--ablation` flag compares:
1. **Baseline** — `retrieve()`
2. **+Quality Boost** — `retrieve_with_quality_boost()`

For ablation, quality scores are pre-set during ingestion: bug-fix memories get higher scores than config memories, simulating real-world access patterns.

### CLI

```bash
python scripts/benchmarks/benchmark_devbench.py              # default, Recall@5
python scripts/benchmarks/benchmark_devbench.py --top-k 3 5  # multiple K values
python scripts/benchmarks/benchmark_devbench.py --ablation    # with quality boost
python scripts/benchmarks/benchmark_devbench.py --markdown    # markdown output
```

### Output

- **Terminal:** Table with per-category results
- **Markdown:** Via `--markdown` flag
- **JSON:** Via `--output-dir` flag

### Expected Results

| Category | Recall@5 | Precision@5 | MRR |
|----------|----------|-------------|-----|
| exact | 0.90+ | 0.20+ | 0.80+ |
| semantic | 0.70+ | 0.15+ | 0.60+ |
| cross-type | 0.60+ | 0.10+ | 0.50+ |
| negative | n/a | 0.00 | n/a |

### Negative Query Metric

`false_positive_rate`: For negative queries, fraction of top-K results carrying any `bench:*` tag. Should be 0.0 (no relevant memories exist for these topics).

## Constraints

- **No LLM dependency** — Pure retrieval, deterministic, offline
- **< 5s runtime** — 30 memories, suitable for CI
- **No CI gate** — Informational only, no thresholds that block builds
- **Self-contained** — Dataset embedded in repo, no downloads needed
- **Reuses locomo_evaluator.py** — Same metric functions, no duplication

## File Structure

```
scripts/benchmarks/
  benchmark_devbench.py     # Main script
  devbench_dataset.json     # Dataset (memories + queries)
  locomo_evaluator.py       # Shared metrics (already exists)
tests/benchmarks/
  test_benchmark_devbench.py  # Tests
```
