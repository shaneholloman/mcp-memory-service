# LoCoMo Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Benchmark mcp-memory-service retrieval quality against the LoCoMo long-term conversational memory benchmark (ACL 2024).

**Architecture:** 4 modules in `scripts/benchmarks/` — dataset loader, metric evaluator, LLM adapter, and main orchestrator. Retrieval-only mode as default (no LLM needed), QA and ablation as optional modes. One isolated SQLite-Vec DB per conversation.

**Tech Stack:** Python 3.11, asyncio, argparse, SQLite-Vec storage backend, ONNX embeddings (all-MiniLM-L6-v2), optional anthropic SDK for QA mode.

**Spec:** `docs/superpowers/specs/2026-03-31-locomo-benchmark-design.md`

---

### Task 1: Dataset Module — Data Structures and Parser

**Files:**
- Create: `scripts/benchmarks/locomo_dataset.py`
- Create: `tests/benchmarks/__init__.py`
- Create: `tests/benchmarks/test_locomo_dataset.py`
- Create: `tests/benchmarks/conftest.py`

- [ ] **Step 1: Write failing tests for data structures and parsing**

```python
# tests/benchmarks/test_locomo_dataset.py
"""Tests for LoCoMo dataset loader."""
import json
import os
import pytest
import tempfile

from locomo_dataset import (
    LocomoTurn,
    LocomoObservation,
    LocomoQA,
    LocomoConversation,
    parse_conversation,
    load_dataset,
)


SAMPLE_LOCOMO_ENTRY = {
    "sample_id": "test_conv_1",
    "conversation": {
        "session_1": [
            {"speaker": "Alice", "dia_id": "d1_1", "text": "I just got a new job at Google."},
            {"speaker": "Bob", "dia_id": "d1_2", "text": "That's amazing! Congrats!"},
        ],
        "session_1_date_time": "January 15, 2024",
        "session_2": [
            {"speaker": "Alice", "dia_id": "d2_1", "text": "Work is going well at Google."},
            {"speaker": "Bob", "dia_id": "d2_2", "text": "How's the team?"},
        ],
        "session_2_date_time": "February 20, 2024",
    },
    "observation": {
        "session_1_observation": "Alice got a new job at Google.\nBob congratulated Alice.",
        "session_2_observation": "Alice says work is going well at Google.",
    },
    "session_summary": {
        "session_1_summary": "Alice shared she got a new job at Google. Bob congratulated her.",
        "session_2_summary": "Alice updated Bob about her job at Google.",
    },
    "event_summary": {},
    "qa": [
        {
            "question": "Where does Alice work?",
            "answer": "Google",
            "category": "single-hop",
            "evidence": ["d1_1"],
        },
        {
            "question": "What happened first, Alice getting the job or Alice saying work is going well?",
            "answer": "Alice getting the job",
            "category": "temporal",
            "evidence": ["d1_1", "d2_1"],
        },
    ],
}


class TestDataStructures:
    def test_locomo_turn_fields(self):
        turn = LocomoTurn(
            speaker="Alice", dia_id="d1_1", text="Hello",
            session_id="session_1", session_date="January 15, 2024",
        )
        assert turn.speaker == "Alice"
        assert turn.dia_id == "d1_1"
        assert turn.text == "Hello"
        assert turn.session_id == "session_1"
        assert turn.session_date == "January 15, 2024"

    def test_locomo_observation_fields(self):
        obs = LocomoObservation(
            session_id="session_1", text="Alice got a job.", speaker="Alice",
        )
        assert obs.session_id == "session_1"

    def test_locomo_qa_fields(self):
        qa = LocomoQA(
            question="Where?", answer="Google",
            category="single-hop", evidence=["d1_1"],
        )
        assert qa.category == "single-hop"
        assert qa.evidence == ["d1_1"]


class TestParseConversation:
    def test_parse_turns(self):
        conv = parse_conversation(SAMPLE_LOCOMO_ENTRY)
        assert conv.sample_id == "test_conv_1"
        assert len(conv.turns) == 4
        assert conv.turns[0].speaker == "Alice"
        assert conv.turns[0].dia_id == "d1_1"
        assert conv.turns[0].session_id == "session_1"
        assert conv.turns[0].session_date == "January 15, 2024"

    def test_parse_observations(self):
        conv = parse_conversation(SAMPLE_LOCOMO_ENTRY)
        assert len(conv.observations) >= 2
        obs_texts = [o.text for o in conv.observations]
        assert "Alice got a new job at Google." in obs_texts

    def test_parse_qa_pairs(self):
        conv = parse_conversation(SAMPLE_LOCOMO_ENTRY)
        assert len(conv.qa_pairs) == 2
        assert conv.qa_pairs[0].category == "single-hop"
        assert conv.qa_pairs[0].evidence == ["d1_1"]

    def test_parse_summaries(self):
        conv = parse_conversation(SAMPLE_LOCOMO_ENTRY)
        assert "session_1" in conv.summaries
        assert "session_2" in conv.summaries


class TestLoadDataset:
    def test_load_from_file(self, tmp_path):
        data_file = tmp_path / "locomo10.json"
        data_file.write_text(json.dumps([SAMPLE_LOCOMO_ENTRY]))
        conversations = load_dataset(str(data_file))
        assert len(conversations) == 1
        assert conversations[0].sample_id == "test_conv_1"

    def test_load_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_dataset("/nonexistent/path/locomo10.json", auto_download=False)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_dataset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'locomo_dataset'`

- [ ] **Step 3: Implement the dataset module**

```python
# scripts/benchmarks/locomo_dataset.py
"""LoCoMo dataset loader and parser.

Loads the LoCoMo benchmark dataset (locomo10.json) and provides
typed data structures for benchmarking memory retrieval.

Reference: https://github.com/snap-research/locomo
"""
import json
import logging
import os
import urllib.request
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

LOCOMO_RAW_URL = (
    "https://raw.githubusercontent.com/snap-research/locomo/main/data/locomo10.json"
)
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "locomo"
)
DEFAULT_DATA_PATH = os.path.join(DEFAULT_DATA_DIR, "locomo10.json")


@dataclass
class LocomoTurn:
    """A single dialog turn in a conversation session."""
    speaker: str
    dia_id: str
    text: str
    session_id: str
    session_date: str


@dataclass
class LocomoObservation:
    """A factual assertion extracted from a conversation session."""
    session_id: str
    text: str
    speaker: str


@dataclass
class LocomoQA:
    """A question-answer pair with category and evidence annotations."""
    question: str
    answer: str
    category: str       # single-hop, multi-hop, temporal, commonsense, adversarial
    evidence: List[str] # dia_ids that support the answer


@dataclass
class LocomoConversation:
    """A complete LoCoMo conversation with all annotations."""
    sample_id: str
    turns: List[LocomoTurn] = field(default_factory=list)
    observations: List[LocomoObservation] = field(default_factory=list)
    summaries: Dict[str, str] = field(default_factory=dict)
    qa_pairs: List[LocomoQA] = field(default_factory=list)


def _extract_session_ids(conversation: dict) -> List[str]:
    """Extract sorted session IDs from conversation dict."""
    session_ids = []
    for key in conversation:
        if key.startswith("session_") and not key.endswith(("_date_time",)):
            session_ids.append(key)
    return sorted(session_ids, key=lambda s: int(s.split("_")[1]))


def parse_conversation(entry: dict) -> LocomoConversation:
    """Parse a single LoCoMo JSON entry into a LocomoConversation."""
    conv_data = entry["conversation"]
    session_ids = _extract_session_ids(conv_data)

    turns: List[LocomoTurn] = []
    for sid in session_ids:
        session_date = conv_data.get(f"{sid}_date_time", "")
        for turn_data in conv_data[sid]:
            turns.append(LocomoTurn(
                speaker=turn_data["speaker"],
                dia_id=turn_data["dia_id"],
                text=turn_data["text"],
                session_id=sid,
                session_date=session_date,
            ))

    observations: List[LocomoObservation] = []
    obs_data = entry.get("observation", {})
    for sid in session_ids:
        obs_key = f"{sid}_observation"
        if obs_key not in obs_data:
            continue
        raw_text = obs_data[obs_key]
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            # Infer speaker from observation text (first name mentioned)
            speaker = ""
            for turn in turns:
                if turn.session_id == sid and turn.speaker.split()[0] in line:
                    speaker = turn.speaker
                    break
            observations.append(LocomoObservation(
                session_id=sid, text=line, speaker=speaker,
            ))

    summaries: Dict[str, str] = {}
    for sid in session_ids:
        sum_key = f"{sid}_summary"
        if sum_key in entry.get("session_summary", {}):
            summaries[sid] = entry["session_summary"][sum_key]

    qa_pairs: List[LocomoQA] = []
    for qa in entry.get("qa", []):
        qa_pairs.append(LocomoQA(
            question=qa["question"],
            answer=qa["answer"],
            category=qa.get("category", "unknown"),
            evidence=qa.get("evidence", []),
        ))

    return LocomoConversation(
        sample_id=entry.get("sample_id", "unknown"),
        turns=turns,
        observations=observations,
        summaries=summaries,
        qa_pairs=qa_pairs,
    )


def _download_dataset(target_path: str) -> None:
    """Download locomo10.json from GitHub."""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    logger.info("Downloading LoCoMo dataset from %s ...", LOCOMO_RAW_URL)
    urllib.request.urlretrieve(LOCOMO_RAW_URL, target_path)
    logger.info("Saved to %s", target_path)


def load_dataset(
    data_path: Optional[str] = None,
    auto_download: bool = True,
) -> List[LocomoConversation]:
    """Load the LoCoMo dataset from a JSON file.

    Args:
        data_path: Path to locomo10.json. Defaults to data/locomo/locomo10.json.
        auto_download: If True, download the dataset if not found locally.

    Returns:
        List of parsed LocomoConversation objects.
    """
    path = data_path or DEFAULT_DATA_PATH

    if not os.path.exists(path):
        if auto_download:
            _download_dataset(path)
        else:
            raise FileNotFoundError(f"Dataset not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    return [parse_conversation(entry) for entry in raw]
```

- [ ] **Step 4: Make the scripts package importable for tests**

```python
# tests/benchmarks/__init__.py
```

```python
# tests/benchmarks/conftest.py
"""Configure sys.path for benchmark tests."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "benchmarks"))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_dataset.py -v`
Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add scripts/benchmarks/locomo_dataset.py tests/benchmarks/__init__.py tests/benchmarks/test_locomo_dataset.py tests/benchmarks/conftest.py
git commit -m "feat(benchmark): add LoCoMo dataset loader and parser"
```

---

### Task 2: Evaluator Module — Retrieval and QA Metrics

**Files:**
- Create: `scripts/benchmarks/locomo_evaluator.py`
- Create: `tests/benchmarks/test_locomo_evaluator.py`

- [ ] **Step 1: Write failing tests for metrics**

```python
# tests/benchmarks/test_locomo_evaluator.py
"""Tests for LoCoMo benchmark metrics."""
import pytest

from locomo_evaluator import (
    recall_at_k,
    precision_at_k,
    mrr,
    token_f1,
    BenchmarkResult,
    aggregate_results,
)


class TestRecallAtK:
    def test_perfect_recall(self):
        retrieved = ["a", "b", "c"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 1.0

    def test_partial_recall(self):
        retrieved = ["a", "x", "y"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.5

    def test_zero_recall(self):
        retrieved = ["x", "y", "z"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=3) == 0.0

    def test_k_limits_results(self):
        retrieved = ["x", "y", "a", "b"]
        relevant = {"a", "b"}
        assert recall_at_k(retrieved, relevant, k=2) == 0.0
        assert recall_at_k(retrieved, relevant, k=4) == 1.0

    def test_empty_relevant_returns_one(self):
        assert recall_at_k(["a"], set(), k=1) == 1.0


class TestPrecisionAtK:
    def test_perfect_precision(self):
        retrieved = ["a", "b"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=2) == 1.0

    def test_half_precision(self):
        retrieved = ["a", "x"]
        relevant = {"a", "b"}
        assert precision_at_k(retrieved, relevant, k=2) == 0.5

    def test_zero_precision(self):
        retrieved = ["x", "y"]
        relevant = {"a"}
        assert precision_at_k(retrieved, relevant, k=2) == 0.0


class TestMRR:
    def test_first_position(self):
        assert mrr(["a", "b"], {"a"}) == 1.0

    def test_second_position(self):
        assert mrr(["x", "a"], {"a"}) == 0.5

    def test_not_found(self):
        assert mrr(["x", "y"], {"a"}) == 0.0

    def test_multiple_relevant_uses_first(self):
        assert mrr(["x", "a", "b"], {"a", "b"}) == 0.5


class TestTokenF1:
    def test_exact_match(self):
        assert token_f1("Google", "Google") == 1.0

    def test_partial_overlap(self):
        score = token_f1("she works at Google", "Google")
        # precision=1/4, recall=1/1, f1=2*(0.25*1)/(0.25+1) = 0.4
        assert abs(score - 0.4) < 0.01

    def test_no_overlap(self):
        assert token_f1("apple banana", "cherry date") == 0.0

    def test_case_insensitive(self):
        assert token_f1("Google", "google") == 1.0

    def test_empty_prediction(self):
        assert token_f1("", "answer") == 0.0

    def test_empty_gold(self):
        assert token_f1("answer", "") == 0.0


class TestAggregateResults:
    def test_aggregate_by_category(self):
        per_question = [
            {"category": "single-hop", "recall_at_5": 1.0, "mrr": 1.0},
            {"category": "single-hop", "recall_at_5": 0.5, "mrr": 0.5},
            {"category": "temporal", "recall_at_5": 0.0, "mrr": 0.0},
        ]
        result = aggregate_results(
            per_question=per_question,
            conversation_id="all",
            mode="retrieval",
            config={"top_k": [5]},
        )
        assert result.by_category["single-hop"]["recall_at_5"] == 0.75
        assert result.by_category["temporal"]["recall_at_5"] == 0.0
        assert result.overall["recall_at_5"] == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_evaluator.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the evaluator module**

```python
# scripts/benchmarks/locomo_evaluator.py
"""LoCoMo benchmark metrics.

Provides retrieval metrics (Recall@K, Precision@K, MRR) and
QA metrics (token-level F1) for the LoCoMo benchmark.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Recall@K: fraction of relevant items found in top-K retrieved."""
    if not relevant:
        return 1.0
    top_k = retrieved[:k]
    found = sum(1 for item in top_k if item in relevant)
    return found / len(relevant)


def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """Precision@K: fraction of top-K retrieved items that are relevant."""
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    found = sum(1 for item in top_k if item in relevant)
    return found / len(top_k)


def mrr(retrieved: List[str], relevant: Set[str]) -> float:
    """Mean Reciprocal Rank: 1/position of first relevant item."""
    for i, item in enumerate(retrieved):
        if item in relevant:
            return 1.0 / (i + 1)
    return 0.0


def token_f1(predicted: str, gold: str) -> float:
    """Token-level F1 score between predicted and gold answer strings.

    Case-insensitive. Tokenized by whitespace.
    Follows the LoCoMo paper methodology.
    """
    pred_tokens = predicted.lower().split()
    gold_tokens = gold.lower().split()

    if not pred_tokens or not gold_tokens:
        return 0.0

    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0

    pred_counts: Dict[str, int] = defaultdict(int)
    for t in pred_tokens:
        pred_counts[t] += 1
    gold_counts: Dict[str, int] = defaultdict(int)
    for t in gold_tokens:
        gold_counts[t] += 1

    overlap = sum(min(pred_counts[t], gold_counts[t]) for t in common)
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)

    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results."""
    conversation_id: str
    mode: str
    overall: Dict[str, float] = field(default_factory=dict)
    by_category: Dict[str, Dict[str, float]] = field(default_factory=dict)
    by_conversation: Dict[str, Dict[str, float]] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


def aggregate_results(
    per_question: List[Dict[str, Any]],
    conversation_id: str,
    mode: str,
    config: Dict[str, Any],
) -> BenchmarkResult:
    """Aggregate per-question metrics into a BenchmarkResult."""
    if not per_question:
        return BenchmarkResult(
            conversation_id=conversation_id, mode=mode, config=config,
        )

    metric_keys = [
        k for k in per_question[0]
        if k != "category" and isinstance(per_question[0][k], (int, float))
    ]

    overall = {}
    for key in metric_keys:
        values = [q[key] for q in per_question if key in q]
        overall[key] = sum(values) / len(values) if values else 0.0

    by_category: Dict[str, Dict[str, float]] = defaultdict(dict)
    categories = set(q["category"] for q in per_question)
    for cat in categories:
        cat_questions = [q for q in per_question if q["category"] == cat]
        for key in metric_keys:
            values = [q[key] for q in cat_questions if key in q]
            by_category[cat][key] = sum(values) / len(values) if values else 0.0

    return BenchmarkResult(
        conversation_id=conversation_id,
        mode=mode,
        overall=overall,
        by_category=dict(by_category),
        config=config,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_evaluator.py -v`
Expected: All 17 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/locomo_evaluator.py tests/benchmarks/test_locomo_evaluator.py
git commit -m "feat(benchmark): add LoCoMo metrics (Recall@K, Precision@K, MRR, F1)"
```

---

### Task 3: LLM Adapter Module

**Files:**
- Create: `scripts/benchmarks/locomo_llm.py`
- Create: `tests/benchmarks/test_locomo_llm.py`

- [ ] **Step 1: Write failing tests for LLM adapter**

```python
# tests/benchmarks/test_locomo_llm.py
"""Tests for LoCoMo LLM adapter."""
import asyncio
import pytest

from locomo_llm import (
    LLMAdapter,
    build_qa_prompt,
    create_adapter,
    MockAdapter,
)


class TestBuildQAPrompt:
    def test_includes_question(self):
        prompt = build_qa_prompt("Where does Alice work?", ["Alice works at Google."])
        assert "Where does Alice work?" in prompt

    def test_includes_context(self):
        prompt = build_qa_prompt("question", ["fact one", "fact two"])
        assert "fact one" in prompt
        assert "fact two" in prompt

    def test_instructs_concise_answer(self):
        prompt = build_qa_prompt("question", ["context"])
        assert "concise" in prompt.lower() or "short" in prompt.lower() or "brief" in prompt.lower()


class TestMockAdapter:
    def test_mock_returns_first_context(self):
        adapter = MockAdapter()
        result = asyncio.run(
            adapter.generate_answer("What?", ["Google is a company."])
        )
        assert result == "Google is a company."

    def test_mock_returns_not_mentioned_when_empty(self):
        adapter = MockAdapter()
        result = asyncio.run(adapter.generate_answer("What?", []))
        assert result == "not mentioned"


class TestCreateAdapter:
    def test_create_mock(self):
        adapter = create_adapter("mock")
        assert isinstance(adapter, MockAdapter)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM"):
            create_adapter("nonexistent_llm")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_llm.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement the LLM adapter module**

```python
# scripts/benchmarks/locomo_llm.py
"""Pluggable LLM adapters for LoCoMo QA mode.

Only imported when --mode qa is used. No LLM dependency for retrieval/ablation.
"""
import logging
from typing import List, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

QA_PROMPT_TEMPLATE = """Answer the following question based ONLY on the provided context.
Give a brief, concise answer. If the answer is not in the context, say "not mentioned".

Context:
{context}

Question: {question}

Answer:"""


def build_qa_prompt(question: str, context: List[str]) -> str:
    """Build the QA prompt from question and retrieved memory contexts."""
    context_text = "\n".join(f"- {c}" for c in context)
    return QA_PROMPT_TEMPLATE.format(context=context_text, question=question)


@runtime_checkable
class LLMAdapter(Protocol):
    """Protocol for LLM answer generation."""
    async def generate_answer(self, question: str, context: List[str]) -> str: ...


class MockAdapter:
    """Mock adapter for testing -- returns the first context line."""
    async def generate_answer(self, question: str, context: List[str]) -> str:
        if context:
            return context[0]
        return "not mentioned"


class ClaudeAdapter:
    """Claude API adapter via anthropic SDK."""
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic SDK: pip install anthropic")
        self.client = anthropic.AsyncAnthropic()
        self.model = model

    async def generate_answer(self, question: str, context: List[str]) -> str:
        prompt = build_qa_prompt(question, context)
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()


class OllamaAdapter:
    """Ollama local LLM adapter via HTTP."""
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def generate_answer(self, question: str, context: List[str]) -> str:
        import aiohttp
        prompt = build_qa_prompt(question, context)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            ) as resp:
                data = await resp.json()
                return data.get("response", "").strip()


def create_adapter(llm_name: str, model: str = "") -> LLMAdapter:
    """Factory to create an LLM adapter.

    Args:
        llm_name: One of 'claude', 'ollama', 'mock'.
        model: Optional model override.
    """
    if llm_name == "mock":
        return MockAdapter()
    elif llm_name == "claude":
        return ClaudeAdapter(model=model or "claude-sonnet-4-20250514")
    elif llm_name == "ollama":
        return OllamaAdapter(model=model or "llama3")
    else:
        raise ValueError(f"Unknown LLM: {llm_name}. Supported: claude, ollama, mock")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/benchmarks/test_locomo_llm.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/locomo_llm.py tests/benchmarks/test_locomo_llm.py
git commit -m "feat(benchmark): add pluggable LLM adapter for LoCoMo QA mode"
```

---

### Task 4: Main Benchmark Script — Ingestion

**Files:**
- Create: `scripts/benchmarks/benchmark_locomo.py`
- Create: `tests/benchmarks/test_benchmark_locomo.py`

- [ ] **Step 1: Write failing tests for ingestion**

```python
# tests/benchmarks/test_benchmark_locomo.py
"""Tests for the main LoCoMo benchmark orchestrator."""
import asyncio
import hashlib
import os
import shutil
import sys
import tempfile

import pytest

from locomo_dataset import LocomoConversation, LocomoObservation, LocomoTurn, LocomoQA

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from benchmark_locomo import (
    ingest_conversation,
    build_evidence_map,
    create_isolated_storage,
)


def _make_test_conversation() -> LocomoConversation:
    return LocomoConversation(
        sample_id="test_1",
        turns=[
            LocomoTurn("Alice", "d1_1", "I work at Google.", "session_1", "January 15, 2024"),
            LocomoTurn("Bob", "d1_2", "Nice!", "session_1", "January 15, 2024"),
        ],
        observations=[
            LocomoObservation("session_1", "Alice works at Google.", "Alice"),
            LocomoObservation("session_1", "Bob congratulated Alice.", "Bob"),
        ],
        summaries={"session_1": "Alice told Bob about her job at Google."},
        qa_pairs=[
            LocomoQA("Where does Alice work?", "Google", "single-hop", ["d1_1"]),
        ],
    )


class TestBuildEvidenceMap:
    def test_maps_dia_ids_to_turns(self):
        conv = _make_test_conversation()
        emap = build_evidence_map(conv)
        assert "d1_1" in emap
        assert "I work at Google." in emap["d1_1"]

    def test_all_dia_ids_present(self):
        conv = _make_test_conversation()
        emap = build_evidence_map(conv)
        assert "d1_1" in emap
        assert "d1_2" in emap


class TestCreateIsolatedStorage:
    def test_creates_storage(self):
        storage, tmp_dir = create_isolated_storage()
        assert storage is not None
        assert os.path.isdir(tmp_dir)
        shutil.rmtree(tmp_dir, ignore_errors=True)


class TestIngestConversation:
    def test_ingest_stores_observations(self):
        conv = _make_test_conversation()
        storage, tmp_dir = create_isolated_storage()
        try:
            count = asyncio.run(self._run_ingest(storage, conv))
            assert count == 2  # 2 observations
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _run_ingest(self, storage, conv):
        await storage.initialize()
        return await ingest_conversation(storage, conv)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ingestion logic**

```python
# scripts/benchmarks/benchmark_locomo.py
#!/usr/bin/env python3
"""LoCoMo Benchmark for MCP Memory Service.

Benchmarks memory retrieval quality against the LoCoMo long-term
conversational memory benchmark (ACL 2024).

Usage:
    python scripts/benchmarks/benchmark_locomo.py                        # retrieval-only
    python scripts/benchmarks/benchmark_locomo.py --top-k 5 10 20       # multiple K
    python scripts/benchmarks/benchmark_locomo.py --mode qa --llm claude # full QA
    python scripts/benchmarks/benchmark_locomo.py --mode ablation        # feature comparison
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from mcp_memory_service.models.memory import Memory
from mcp_memory_service.storage.sqlite_vec import SqliteVecMemoryStorage

from locomo_dataset import LocomoConversation, load_dataset
from locomo_evaluator import (
    BenchmarkResult,
    aggregate_results,
    mrr,
    precision_at_k,
    recall_at_k,
    token_f1,
)

logger = logging.getLogger(__name__)


def create_isolated_storage() -> Tuple[SqliteVecMemoryStorage, str]:
    """Create an isolated SQLite-Vec storage in a temp directory."""
    tmp_dir = tempfile.mkdtemp(prefix="locomo-bench-")
    db_path = os.path.join(tmp_dir, "memories.db")
    storage = SqliteVecMemoryStorage(db_path)
    return storage, tmp_dir


def build_evidence_map(conv: LocomoConversation) -> Dict[str, str]:
    """Build a mapping from dia_id to turn text."""
    return {turn.dia_id: turn.text for turn in conv.turns}


def _parse_session_date(date_str: str) -> float:
    """Parse a LoCoMo session date string to a Unix timestamp."""
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.timestamp()
        except ValueError:
            continue
    return datetime.now().timestamp()


async def ingest_conversation(
    storage: SqliteVecMemoryStorage,
    conv: LocomoConversation,
) -> int:
    """Ingest all observations from a conversation as memories.

    Returns number of successfully stored memories.
    """
    stored = 0
    for obs in conv.observations:
        session_date = ""
        for turn in conv.turns:
            if turn.session_id == obs.session_id:
                session_date = turn.session_date
                break

        created_at = _parse_session_date(session_date) if session_date else None
        content_hash = hashlib.sha256(obs.text.encode("utf-8")).hexdigest()

        memory = Memory(
            content=obs.text,
            content_hash=content_hash,
            tags=["locomo", conv.sample_id, obs.speaker, obs.session_id],
            memory_type="observation",
            created_at=int(created_at) if created_at else None,
        )

        success, msg = await storage.store(memory, skip_semantic_dedup=True)
        if success:
            stored += 1
        else:
            logger.debug("Skip store: %s", msg)

    return stored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/benchmark_locomo.py tests/benchmarks/test_benchmark_locomo.py
git commit -m "feat(benchmark): add LoCoMo ingestion -- store observations as memories"
```

---

### Task 5: Main Benchmark Script — Retrieval Evaluation

**Files:**
- Modify: `scripts/benchmarks/benchmark_locomo.py`
- Modify: `tests/benchmarks/test_benchmark_locomo.py`

- [ ] **Step 1: Write failing test for retrieval evaluation**

Append to `tests/benchmarks/test_benchmark_locomo.py`:

```python
from benchmark_locomo import evaluate_retrieval


class TestEvaluateRetrieval:
    def test_retrieval_returns_per_question_results(self):
        conv = _make_test_conversation()
        storage, tmp_dir = create_isolated_storage()
        try:
            results = asyncio.run(self._run_retrieval(storage, conv))
            assert len(results) == 1  # 1 QA pair
            assert "category" in results[0]
            assert "recall_at_5" in results[0]
            assert "precision_at_5" in results[0]
            assert "mrr" in results[0]
            assert results[0]["category"] == "single-hop"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _run_retrieval(self, storage, conv):
        await storage.initialize()
        await ingest_conversation(storage, conv)
        evidence_map = build_evidence_map(conv)
        return await evaluate_retrieval(storage, conv, evidence_map, top_k=[5])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py::TestEvaluateRetrieval -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_retrieval'`

- [ ] **Step 3: Implement retrieval evaluation**

Add to `scripts/benchmarks/benchmark_locomo.py`:

```python
async def evaluate_retrieval(
    storage: SqliteVecMemoryStorage,
    conv: LocomoConversation,
    evidence_map: Dict[str, str],
    top_k: List[int] = None,
) -> List[Dict]:
    """Evaluate retrieval quality for all QA pairs in a conversation.

    For each question, searches memories and checks if evidence turns
    are represented in the results via substring matching.
    """
    if top_k is None:
        top_k = [5]
    max_k = max(top_k)

    per_question = []
    for qa in conv.qa_pairs:
        results = await storage.retrieve(qa.question, n_results=max_k)
        retrieved_texts = [r.memory.content for r in results]

        # Collect evidence texts
        relevant_evidence = set()
        for dia_id in qa.evidence:
            if dia_id in evidence_map:
                relevant_evidence.add(evidence_map[dia_id])

        # For each retrieved text, check if it matches any evidence
        # (substring match in either direction: evidence in retrieved or retrieved in evidence)
        binary_retrieved = []
        for text in retrieved_texts:
            is_match = any(ev in text or text in ev for ev in relevant_evidence)
            binary_retrieved.append(
                "relevant" if is_match else f"irrelevant_{len(binary_retrieved)}"
            )
        relevant_labels = {"relevant"}

        metrics = {"category": qa.category}
        for k in top_k:
            metrics[f"recall_at_{k}"] = recall_at_k(binary_retrieved, relevant_labels, k)
            metrics[f"precision_at_{k}"] = precision_at_k(binary_retrieved, relevant_labels, k)
        metrics["mrr"] = mrr(binary_retrieved, relevant_labels)

        per_question.append(metrics)

    return per_question
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py::TestEvaluateRetrieval -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/benchmark_locomo.py tests/benchmarks/test_benchmark_locomo.py
git commit -m "feat(benchmark): add LoCoMo retrieval evaluation (Recall@K, Precision@K, MRR)"
```

---

### Task 6: Main Benchmark Script — CLI, Output, and QA Mode

**Files:**
- Modify: `scripts/benchmarks/benchmark_locomo.py`

- [ ] **Step 1: Implement output formatting, QA mode, and CLI**

Add to `scripts/benchmarks/benchmark_locomo.py`:

```python
def format_results_table(result: BenchmarkResult) -> str:
    """Format benchmark results as a readable terminal table."""
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"LoCoMo Benchmark Results -- Mode: {result.mode}")
    lines.append(f"Config: {result.config}")
    lines.append(f"{'='*70}")

    lines.append(f"\n  Overall:")
    for key, val in sorted(result.overall.items()):
        lines.append(f"    {key:20s}: {val:.4f}")

    lines.append(f"\n  By Category:")
    for cat in sorted(result.by_category.keys()):
        lines.append(f"    {cat}:")
        for key, val in sorted(result.by_category[cat].items()):
            lines.append(f"      {key:20s}: {val:.4f}")

    lines.append(f"{'='*70}\n")
    return "\n".join(lines)


def format_results_markdown(result: BenchmarkResult) -> str:
    """Format benchmark results as a Markdown table."""
    if not result.overall:
        return "No results."

    metric_keys = sorted(result.overall.keys())
    lines = []
    lines.append("| Category | " + " | ".join(metric_keys) + " |")
    lines.append("|" + "---|" * (len(metric_keys) + 1))

    vals = " | ".join(f"{result.overall[k]:.4f}" for k in metric_keys)
    lines.append(f"| **Overall** | {vals} |")

    for cat in sorted(result.by_category.keys()):
        vals = " | ".join(
            f"{result.by_category[cat].get(k, 0):.4f}" for k in metric_keys
        )
        lines.append(f"| {cat} | {vals} |")

    return "\n".join(lines)


def save_results(result: BenchmarkResult, output_dir: str) -> str:
    """Save results as JSON. Returns the file path."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{result.mode}.json"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w") as f:
        json.dump({
            "conversation_id": result.conversation_id,
            "mode": result.mode,
            "overall": result.overall,
            "by_category": result.by_category,
            "by_conversation": result.by_conversation,
            "config": result.config,
            "timestamp": timestamp,
        }, f, indent=2)
    return filepath


async def evaluate_qa(
    storage: SqliteVecMemoryStorage,
    conv: LocomoConversation,
    evidence_map: Dict[str, str],
    adapter,
    top_k: List[int] = None,
) -> List[Dict]:
    """Evaluate QA with LLM answer generation."""
    if top_k is None:
        top_k = [5]
    k = max(top_k)

    per_question = []
    for qa in conv.qa_pairs:
        results = await storage.retrieve(qa.question, n_results=k)
        context = [r.memory.content for r in results]
        predicted = await adapter.generate_answer(qa.question, context)
        f1 = token_f1(predicted, qa.answer)
        metrics = {"category": qa.category, "f1": f1}
        per_question.append(metrics)

    return per_question


async def run_benchmark(args: argparse.Namespace) -> BenchmarkResult:
    """Run the full benchmark pipeline."""
    print("Loading LoCoMo dataset...")
    conversations = load_dataset(args.data_path)
    print(f"Loaded {len(conversations)} conversations")

    all_per_question = []

    for conv in conversations:
        print(f"\n--- Conversation: {conv.sample_id} ---")
        print(f"  Turns: {len(conv.turns)}, Observations: {len(conv.observations)}, QA: {len(conv.qa_pairs)}")

        storage, tmp_dir = create_isolated_storage()
        try:
            await storage.initialize()
            count = await ingest_conversation(storage, conv)
            print(f"  Ingested: {count} memories")

            evidence_map = build_evidence_map(conv)

            if args.mode == "retrieval":
                per_q = await evaluate_retrieval(
                    storage, conv, evidence_map, args.top_k,
                )
                all_per_question.extend(per_q)

            elif args.mode == "ablation":
                ablation_results = await run_ablation(
                    storage, conv, evidence_map, args.top_k,
                )
                all_per_question.extend(ablation_results)

            elif args.mode == "qa":
                from locomo_llm import create_adapter
                adapter = create_adapter(args.llm, args.llm_model or "")
                per_q = await evaluate_qa(
                    storage, conv, evidence_map, adapter, args.top_k,
                )
                all_per_question.extend(per_q)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    result = aggregate_results(
        per_question=all_per_question,
        conversation_id="all",
        mode=args.mode,
        config={"top_k": args.top_k, "llm": getattr(args, "llm", None)},
    )

    return result


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LoCoMo Benchmark for MCP Memory Service",
    )
    parser.add_argument(
        "--data-path", type=str, default=None,
        help="Path to locomo10.json (auto-downloads if not specified)",
    )
    parser.add_argument(
        "--mode", choices=["retrieval", "qa", "ablation"], default="retrieval",
        help="Mode: retrieval (default), qa, or ablation",
    )
    parser.add_argument(
        "--top-k", type=int, nargs="+", default=[5],
        help="K values for Recall@K / Precision@K (default: 5)",
    )
    parser.add_argument(
        "--llm", type=str, default="claude",
        help="LLM backend for QA mode (claude, ollama, mock)",
    )
    parser.add_argument(
        "--llm-model", type=str, default=None,
        help="Model name override for LLM backend",
    )
    parser.add_argument(
        "--markdown", action="store_true",
        help="Output results as Markdown table",
    )
    parser.add_argument(
        "--output-dir", type=str,
        default=os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "locomo", "results",
        ),
        help="Directory to save JSON results",
    )
    return parser.parse_args(argv)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    result = asyncio.run(run_benchmark(args))

    if args.markdown:
        print(format_results_markdown(result))
    else:
        print(format_results_table(result))

    filepath = save_results(result, args.output_dir)
    print(f"Results saved to: {filepath}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test CLI manually**

Run: `.venv/bin/python scripts/benchmarks/benchmark_locomo.py --help`
Expected: Help text with all arguments shown

- [ ] **Step 3: Commit**

```bash
git add scripts/benchmarks/benchmark_locomo.py
git commit -m "feat(benchmark): add CLI, output formatting, and QA evaluation mode"
```

---

### Task 7: Ablation Mode

**Files:**
- Modify: `scripts/benchmarks/benchmark_locomo.py`
- Modify: `tests/benchmarks/test_benchmark_locomo.py`

- [ ] **Step 1: Write failing test for ablation**

Append to `tests/benchmarks/test_benchmark_locomo.py`:

```python
from benchmark_locomo import run_ablation


class TestAblation:
    def test_ablation_returns_multiple_configs(self):
        conv = _make_test_conversation()
        storage, tmp_dir = create_isolated_storage()
        try:
            results = asyncio.run(self._run_ablation(storage, conv))
            assert len(results) >= 2
            assert all("config_name" in r for r in results)
            config_names = {r["config_name"] for r in results}
            assert "baseline" in config_names
            assert "+quality_boost" in config_names
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _run_ablation(self, storage, conv):
        await storage.initialize()
        await ingest_conversation(storage, conv)
        evidence_map = build_evidence_map(conv)
        return await run_ablation(storage, conv, evidence_map, top_k=[5])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py::TestAblation -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement ablation mode**

Add to `scripts/benchmarks/benchmark_locomo.py` (before `run_benchmark`):

```python
async def run_ablation(
    storage: SqliteVecMemoryStorage,
    conv: LocomoConversation,
    evidence_map: Dict[str, str],
    top_k: List[int] = None,
) -> List[Dict]:
    """Run ablation study comparing retrieval configurations.

    Configurations:
    1. Baseline -- retrieve() with cosine similarity
    2. +Quality -- retrieve_with_quality_boost()
    """
    if top_k is None:
        top_k = [5]
    max_k = max(top_k)

    configs = [
        ("baseline", "retrieve"),
        ("+quality_boost", "retrieve_with_quality_boost"),
    ]

    all_results = []
    for config_name, method_name in configs:
        for qa in conv.qa_pairs:
            if method_name == "retrieve":
                results = await storage.retrieve(qa.question, n_results=max_k)
            elif method_name == "retrieve_with_quality_boost":
                results = await storage.retrieve_with_quality_boost(
                    qa.question, n_results=max_k,
                )
            else:
                continue

            retrieved_texts = [r.memory.content for r in results]
            relevant_evidence = set()
            for dia_id in qa.evidence:
                if dia_id in evidence_map:
                    relevant_evidence.add(evidence_map[dia_id])

            binary_retrieved = []
            for text in retrieved_texts:
                is_match = any(
                    ev in text or text in ev for ev in relevant_evidence
                )
                binary_retrieved.append(
                    "relevant" if is_match
                    else f"irrelevant_{len(binary_retrieved)}"
                )
            relevant_labels = {"relevant"}

            metrics = {"config_name": config_name, "category": qa.category}
            for k in top_k:
                metrics[f"recall_at_{k}"] = recall_at_k(
                    binary_retrieved, relevant_labels, k,
                )
                metrics[f"precision_at_{k}"] = precision_at_k(
                    binary_retrieved, relevant_labels, k,
                )
            metrics["mrr"] = mrr(binary_retrieved, relevant_labels)

            all_results.append(metrics)

    return all_results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/benchmarks/test_benchmark_locomo.py::TestAblation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/benchmarks/benchmark_locomo.py tests/benchmarks/test_benchmark_locomo.py
git commit -m "feat(benchmark): add ablation mode comparing baseline vs quality-boost"
```

---

### Task 8: Gitignore and Full Test Run

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add data/locomo/ to .gitignore**

Append to `.gitignore`:
```
# LoCoMo benchmark data (downloaded on demand)
data/locomo/
```

- [ ] **Step 2: Run the full benchmark test suite**

Run: `.venv/bin/pytest tests/benchmarks/ -v`
Expected: All tests PASS (~30 tests across 4 files)

- [ ] **Step 3: Run CLI smoke test**

Run: `.venv/bin/python scripts/benchmarks/benchmark_locomo.py --help`
Expected: Clean help output with all arguments

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: add data/locomo/ to gitignore for benchmark dataset"
```

---

### Task Summary

| Task | Description | New Files | Tests |
|------|-------------|-----------|-------|
| 1 | Dataset loader and parser | `locomo_dataset.py` | 8 |
| 2 | Retrieval and QA metrics | `locomo_evaluator.py` | 17 |
| 3 | LLM adapter (pluggable) | `locomo_llm.py` | 5 |
| 4 | Ingestion logic | `benchmark_locomo.py` | 4 |
| 5 | Retrieval evaluation | (modify above) | 1 |
| 6 | CLI, output, QA mode | (modify above) | manual |
| 7 | Ablation mode | (modify above) | 1 |
| 8 | Gitignore + integration | `.gitignore` | full suite |
