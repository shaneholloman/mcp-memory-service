# LoCoMo Benchmark for MCP Memory Service — Design Spec

**Date:** 2026-03-31
**Status:** Approved
**Paper:** "Evaluating Very Long-Term Conversational Memory of LLM Agents" (ACL 2024)
**LoCoMo Repo:** https://github.com/snap-research/locomo

---

## Goal

Benchmark mcp-memory-service against LoCoMo to:
1. Produce reproducible retrieval and QA scores comparable to LoCoMo paper baselines
2. Quantify the value of our advanced features (Quality Boost, Decay, Graph) via ablation

## Architecture

**Approach:** Modular — 4 files in `scripts/benchmarks/`

| File | Responsibility |
|------|---------------|
| `benchmark_locomo.py` | CLI entry, orchestration, ingestion |
| `locomo_dataset.py` | Download, parsing, dataset abstraction |
| `locomo_evaluator.py` | Metrics (Recall@K, Precision@K, MRR, F1) |
| `locomo_llm.py` | Pluggable LLM adapter (only loaded in `qa` mode) |

## Dataset Module (`locomo_dataset.py`)

### Download Logic
- Default path: `data/locomo/locomo10.json`
- Auto-downloads from GitHub Raw URL if missing
- CLI override: `--data-path /path/to/locomo10.json`
- `data/locomo/` added to `.gitignore`

### Data Structures

```python
@dataclass
class LocomoTurn:
    speaker: str
    dia_id: str
    text: str
    session_id: str
    session_date: str

@dataclass
class LocomoObservation:
    session_id: str
    text: str
    speaker: str

@dataclass
class LocomoQA:
    question: str
    answer: str
    category: str       # single-hop, multi-hop, temporal, commonsense, adversarial
    evidence: List[str] # dia_ids that support the answer

@dataclass
class LocomoConversation:
    sample_id: str
    turns: List[LocomoTurn]
    observations: List[LocomoObservation]
    summaries: Dict[str, str]   # session_id -> summary
    qa_pairs: List[LocomoQA]
```

### API

```python
async def load_dataset(data_path: Optional[str] = None) -> List[LocomoConversation]
```

## Ingestion Strategy

Per conversation: isolated SQLite-Vec DB in a temp directory to prevent cross-contamination.

```python
async def ingest_conversation(storage, conversation: LocomoConversation) -> int
```

Each observation stored as a Memory with:
- `content`: observation text
- `tags`: `["locomo", sample_id, speaker, session_id]`
- `memory_type`: `"observation"`
- `created_at`: timestamp parsed from `session_date` (critical for temporal questions)
- `content_hash`: generated from content

**Evidence mapping:** During ingestion, build a lookup `dia_id → content_hash` so retrieval results can be matched against ground-truth evidence.

## Evaluation Modes

Three modes via `--mode` CLI flag:

### Mode 1: `retrieval` (Default)

Retrieval-only — no LLM needed, deterministic, free.

```
For each QA pair:
  1. memory_search(question, n_results=K)
  2. Check if evidence dia_ids appear in retrieved memories
  3. Compute Recall@K, Precision@K, MRR
```

### Mode 2: `qa`

Full QA evaluation — requires LLM.

```
For each QA pair:
  1. memory_search(question, n_results=K)
  2. LLM generates answer from retrieved context + question
  3. Compute token-level F1 against gold answer
```

### Mode 3: `ablation`

Feature comparison — runs retrieval mode with 4 configurations:

1. **Baseline** — `retrieve()` (naive cosine similarity)
2. **+Quality** — `retrieve_with_quality_boost()`
3. **+Decay** — Baseline with temporal decay scoring
4. **+All** — Quality + Decay + Graph relationships

Output: delta table per feature per category.

## Evaluator (`locomo_evaluator.py`)

### Retrieval Metrics

```python
def recall_at_k(retrieved_hashes: List[str], relevant_hashes: Set[str], k: int) -> float
def precision_at_k(retrieved_hashes: List[str], relevant_hashes: Set[str], k: int) -> float
def mrr(retrieved_hashes: List[str], relevant_hashes: Set[str]) -> float
```

### QA Metrics

```python
def token_f1(predicted: str, gold: str) -> float
```

### Result Structure

```python
@dataclass
class BenchmarkResult:
    conversation_id: str
    mode: str
    overall: Dict[str, float]
    by_category: Dict[str, Dict[str, float]]
    by_conversation: Dict[str, Dict[str, float]]
    config: Dict[str, Any]
```

### Output Formats
- **Terminal:** Table with per-category results
- **JSON:** `data/locomo/results/<timestamp>_<mode>.json`
- **Markdown:** Optional via `--markdown` for README/paper inclusion

## LLM Adapter (`locomo_llm.py`)

Only imported when `--mode qa`. No LLM dependency for retrieval/ablation modes.

```python
class LLMAdapter(Protocol):
    async def generate_answer(self, question: str, context: List[str]) -> str: ...

class ClaudeAdapter(LLMAdapter): ...   # Default, via anthropic SDK
class OllamaAdapter(LLMAdapter): ...   # Local, via HTTP
```

CLI: `--llm claude --llm-model claude-sonnet-4-20250514` or `--llm ollama --llm-model llama3`

Prompt template: question + retrieved memories as context → answer. Kept simple, analogous to the LoCoMo paper approach.

## CLI Interface

```bash
# Retrieval-only (default, free, deterministic)
python scripts/benchmarks/benchmark_locomo.py

# Adjustable K values
python scripts/benchmarks/benchmark_locomo.py --top-k 5 10 20

# Full QA evaluation
python scripts/benchmarks/benchmark_locomo.py --mode qa --llm claude

# Ablation: feature comparison
python scripts/benchmarks/benchmark_locomo.py --mode ablation

# Custom dataset path
python scripts/benchmarks/benchmark_locomo.py --data-path /path/to/locomo10.json

# Markdown output
python scripts/benchmarks/benchmark_locomo.py --markdown
```

## Key Design Decisions

1. **Isolated DBs per conversation** — prevents cross-contamination, enables parallel evaluation
2. **Retrieval-only as default** — deterministic, free, CI-friendly
3. **Evidence-based retrieval eval** — uses LoCoMo's `evidence` dia_ids, not just answer matching
4. **LLM adapter lazy-loaded** — no anthropic/ollama dependency unless `--mode qa`
5. **Download on demand** — no git submodule, cached in `data/locomo/`
6. **Temporal timestamps preserved** — observations get session timestamps for decay scoring eval

## MCP Memory Service Features Under Test

| Feature | LoCoMo Category | How Tested |
|---------|----------------|------------|
| Semantic search (cosine) | All categories | Baseline retrieval |
| Quality boost scoring | Adversarial | Filter low-relevance results |
| Temporal decay | Temporal | Time-weighted retrieval |
| Graph relationships | Multi-hop | Cross-memory link traversal |
| Memory consolidation | Event summarization | Future extension |
| Semantic dedup | Ingestion quality | Observation dedup during ingest |
