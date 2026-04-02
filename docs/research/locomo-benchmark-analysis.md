# LoCoMo Benchmark Analysis

**Paper**: "Evaluating Very Long-Term Conversational Memory of LLM Agents" (ACL 2024)
**Authors**: Adyasha Maharana, Dong-Ho Lee, Sergey Tulyakov, Mohit Bansal, Francesco Barbieri, Yuwei Fang (UNC Chapel Hill, USC, Snap Inc.)
**arXiv**: https://arxiv.org/abs/2402.17753
**GitHub**: https://github.com/snap-research/locomo (698 stars, 75 forks)
**Project Page**: https://snap-research.github.io/locomo/

---

## 1. What is LoCoMo?

LoCoMo (Long-term Conversational Memory) is a benchmark for evaluating how well LLM agents handle **very long-term conversational memory** -- conversations spanning up to 35 sessions, ~300 turns, and ~9K tokens on average. It goes beyond existing long-term dialogue benchmarks that cap at 5 sessions.

The dataset is generated via a machine-human pipeline:
- Two LLM-based **virtual agents** converse over many sessions
- Each agent is assigned **persona statements** and a **temporal event graph** (realistic life events with causal/temporal connections)
- Agents use a **memory and reflection module** to retrieve relevant history
- Agents can share and react to **images** (multimodal)
- Human annotators **verify and refine** the conversations for consistency

## 2. Dataset Structure

**File**: `data/locomo10.json` -- 10 annotated conversations

Each sample in the JSON contains:

| Field | Type | Description |
|-------|------|-------------|
| `sample_id` | string | Unique conversation identifier |
| `conversation` | object | Sessions with timestamps; includes `speaker_a`, `speaker_b` |
| `conversation.session_<num>` | list | List of turns for session N |
| `conversation.session_<num>_date_time` | string | Timestamp for session N |
| `observation` | object (generated) | Per-session observations (`session_<num>_observation`) -- assertions about speakers' lives |
| `session_summary` | object (generated) | Per-session summaries (`session_<num>_summary`) |
| `event_summary` | object (annotated) | Per-speaker significant events per session (`events_session_<num>`) -- ground truth for event summarization |
| `qa` | list (annotated) | Question-answer pairs with `question`, `answer`, `category`, `evidence` (dialog IDs) |

**Turn structure** within a session:
- `speaker`: name of the speaker
- `dia_id`: dialog turn identifier
- `text`: content of the dialog
- `img_url` (optional): link to shared image
- `blip_caption` (optional): BLIP-generated image caption
- Search query used by icrawler to retrieve the image

## 3. Evaluation Tasks

### Task 1: Question Answering (QA)
Direct examination of memory via QA. Five reasoning categories:

| Category | Description |
|----------|-------------|
| **Single-hop** | Answer from a single conversation turn |
| **Multi-hop** | Requires combining info from multiple turns/sessions |
| **Temporal** | Requires understanding time-based relationships (when, sequence, duration) |
| **Commonsense/World Knowledge** | Requires external knowledge combined with conversation context |
| **Adversarial** | Questions designed to test hallucination resistance (correct answer may be "not mentioned") |

**Metric**: F1-score on predicted answers.

### Task 2: Event Graph Summarization
Extract causal and temporal event chains for each speaker across sessions.

**Ground truth**: Human-annotated event graphs (temporal event sequences per speaker).
**Metric**: Likely ROUGE-based (evaluation code marked "coming soon" in repo).

### Task 3: Multimodal Dialog Generation
Generate contextually appropriate responses using recalled conversation history, including image understanding.

**Metric**: MM-Relevance score (multimodal relevance).

## 4. RAG Evaluation Setup

The benchmark evaluates RAG with three different retrieval databases:

| Database Type | Source | Description |
|---------------|--------|-------------|
| **Dialogs** | Raw conversation turns | Direct retrieval over dialog text |
| **Observations** | GPT-3.5 generated | Assertions/facts about each speaker's life extracted from sessions |
| **Session Summaries** | GPT-3.5 generated | Condensed summaries of each session |

**Key finding**: RAG with **observations** (factual assertions) performs best, as they transform messy dialog into structured knowledge -- very relevant for memory services.

## 5. Baseline Results (Key Findings)

- Long-context LLMs and RAG improve QA by 22-66% over base models
- All models still lag behind human performance by ~56%
- **Temporal reasoning** is the hardest category (73% below human)
- Long-context LLMs hallucinate significantly on adversarial questions
- RAG offers the best accuracy/comprehension tradeoff
- Observations-based RAG outperforms raw dialog RAG

## 6. GitHub Repository Structure

```
snap-research/locomo/
├── data/                    # Dataset files
│   ├── locomo10.json        # Main benchmark (10 conversations)
│   └── multimodal_dialog/   # Example agent configs
├── generative_agents/       # LLM agent architecture for conversation generation
├── scripts/                 # Shell scripts for all tasks
│   ├── generate_conversations.sh
│   ├── generate_observations.sh
│   ├── generate_session_summaries.sh
│   ├── evaluate_rag_gpts.sh
│   └── evaluate_claude.sh
├── task_eval/               # Evaluation code for tasks
├── prompt_examples/         # Prompt templates
├── static/                  # Images, paper PDF
├── global_methods.py        # Shared utilities
└── README.MD
```

## 7. Benchmarking MCP Memory Service Against LoCoMo

### Direct Alignment (High Relevance)

The MCP Memory Service's architecture maps naturally to the LoCoMo RAG evaluation:

| LoCoMo Concept | MCP Memory Service Equivalent |
|----------------|-------------------------------|
| Observations database | Stored memories (semantic content) |
| Vector retrieval over observations | `memory_search` with embeddings (all-MiniLM-L6-v2) |
| Session summaries | Could be generated via `memory_consolidate` |
| QA with retrieved context | Retrieve memories, feed to LLM for answer |
| Temporal reasoning | Memory timestamps + temporal metadata |
| Multi-hop reasoning | Multiple memory retrievals + graph relationships |

### Proposed Benchmark Approach

#### Phase 1: Data Ingestion
1. Parse `locomo10.json` conversations
2. For each session, generate observations/assertions (or use pre-generated ones)
3. Store each observation as a memory via `memory_store` with:
   - Content: the observation text
   - Tags: speaker name, session number, conversation ID
   - Metadata: timestamp from `session_<num>_date_time`
   - Memory type: appropriate classification

#### Phase 2: QA Evaluation
1. For each QA pair in the dataset:
   - Use the `question` as a semantic search query via `memory_search`
   - Retrieve top-K memories
   - Feed retrieved context + question to an LLM
   - Compare predicted answer to ground truth `answer`
   - Compute F1-score
2. Break down results by `category` (single-hop, multi-hop, temporal, adversarial, commonsense)

#### Phase 3: Advanced Evaluation
- **Temporal**: Test if memory timestamps + decay scoring help temporal questions
- **Multi-hop**: Test if graph relationships (`memory_graph`) improve multi-hop retrieval
- **Adversarial**: Test if quality scoring helps filter irrelevant retrievals
- **Event summarization**: Use `memory_consolidate` to generate event summaries, compare to ground truth

### Key Metrics to Track

| Metric | Task | How to Compute |
|--------|------|----------------|
| F1-score | QA | Token-level F1 between predicted and gold answer |
| Recall@K | Retrieval | % of questions where evidence dialog IDs appear in top-K results |
| Category breakdown | QA | F1 per category (single-hop, multi-hop, temporal, etc.) |
| ROUGE-L | Event summarization | Against human-annotated event graphs |
| MM-Relevance | Dialog generation | Multimodal relevance scoring |

### Unique Advantages to Highlight

MCP Memory Service features that could outperform basic RAG:
1. **Quality scoring** -- filter low-quality memories before retrieval
2. **Decay scoring** -- temporal relevance weighting
3. **Graph relationships** -- causal/temporal links between memories
4. **Memory consolidation** -- compress and merge related memories
5. **Semantic deduplication** -- prevent redundant storage
6. **Content hashing** -- exact duplicate prevention

### Implementation Considerations

- LoCoMo has only 10 conversations -- small enough for thorough evaluation
- Each conversation has ~300 turns across ~35 sessions -- realistic memory load
- The `evidence` field in QA annotations enables retrieval quality measurement (not just answer quality)
- Pre-generated observations are available -- no need to regenerate
- Scripts exist for Claude evaluation (`evaluate_claude.sh`) -- adaptable for our service
