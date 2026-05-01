# Multi-Domain Support Triage Agent

A terminal-based AI agent that triages support tickets across **HackerRank**, **Claude**, and **Visa** ecosystems using RAG (Retrieval-Augmented Generation).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TRIAGE PIPELINE                       │
│                                                         │
│  Input CSV → Safety Check → Escalation Rules            │
│           → Injection Detection → Language Check        │
│           → Vagueness Check → RAG Retrieval             │
│           → LLM Reasoning → Validated Output CSV        │
│                                                         │
│  Corpus: 1759 chunks (from 774 docs)                    │
│  Index: Pure-Python TF-IDF + Cosine Similarity         │
│  LLM: Gemini 2.0 Flash (with rate-limit backoff)        │
└─────────────────────────────────────────────────────────┘
```

## Setup

### 1. Install dependencies

```bash
cd code/
pip install -r requirements.txt
```

### 2. Configure API keys

Copy the `.env.example` to `.env` at the project root and add your API key:

```bash
# At project root (parent of code/)
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your-gemini-api-key-here
# OR
OPENAI_API_KEY=your-openai-api-key-here
```

You need at least ONE of Gemini or OpenAI API keys.

### 3. Run the agent

**Important:** You must navigate to the `code/` directory before running the agent.

```bash
cd code/

# Process the actual support tickets
python main.py

# Process sample tickets (for testing/validation)
python main.py --sample
```

Output is written to `support_tickets/output.csv` (or `sample_output.csv`).

### 4. Test the submission

To verify the submission against the evaluation criteria without making heavy API calls:

```bash
python test_submission.py
```

## Module Structure

| Module | Purpose |
|--------|---------|
| `main.py` | Entry point — 7-stage triage orchestrator |
| `config.py` | Configuration, env vars, constants |
| `schemas.py` | Data models with validation |
| `corpus_loader.py` | Load & chunk 774 markdown support docs |
| `indexer.py` | Build pure-Python TF-IDF index (no DLL dependencies) |
| `retriever.py` | Semantic retrieval + re-ranking |
| `safety.py` | Prompt injection, malicious intent, PII detection |
| `escalation.py` | Deterministic rule-based escalation engine |
| `agent.py` | LLM reasoning with Gemini/OpenAI + rate-limit handling |
| `test_submission.py`| Validation script for scoring criteria |

## Design Decisions

1. **RAG over parametric knowledge**: All responses are grounded in the provided corpus, never the model's training data.
2. **Pure-Python Indexer**: Replaced ChromaDB with TF-IDF to eliminate Windows DLL/dependency issues.
3. **Adaptive Rate-Limiting**: Implemented dynamic backoff in `agent.py` to handle Gemini free-tier quotas reliably.
4. **Deterministic escalation first**: High-risk patterns (billing, fraud, security) are caught by regex rules BEFORE hitting the LLM, ensuring safety.
5. **Safety-first pipeline**: Prompt injection and malicious requests are detected early.
6. **Structured JSON output**: LLM produces validated JSON; fallback to escalation if parsing fails.
