# Madhan Support Agent — Week 6

A personal support agent for **Madhan**, built by Karthick. It reads the `docs/`
folder, chunks the markdown, embeds it in a **new Pinecone index**, and answers
questions through a **tool-calling ReAct loop** (max 5 steps, tool chaining) with
**structured model output**, **cross-session memory**, **prompt-injection
guardrails**, **per-turn logging**, and a **reminder/escalation** path to Madhan.

---

## How the code maps to Scope / Harness / Instrumentation / Productionize

The project is organized around four concerns. Use this map to find any piece of code.

| Layer | What it is | Files |
|-------|------------|-------|
| **SCOPE** | *What* the agent is for and the contract it must obey: the system prompt, the structured-output schema, the tool catalog & descriptions, guardrail rules, and the knowledge-domain loader/chunker. | `src/schema.py`, `src/tools.py`, `src/guardrails.py`, `src/document_loader.py`, `src/chunker.py`, system prompt in `src/agent.py` |
| **HARNESS** | *How* the agent runs: the ReAct execution loop, model binding, tool dispatch, step budget, chaining, the retrieval engine it calls, and escalation control-flow. | `src/agent.py`, `src/embedder.py`, `src/knowledge_base.py`, `src/escalation.py` |
| **INSTRUMENTATION** | *Seeing inside* every run: per-turn/per-session logs and the runtime context used to thread session/escalation state through tool calls. | `src/logger.py`, `src/runtime.py` |
| **PRODUCTIONIZE** | *Hardening for real use*: config/secrets, durable memory across runs, the reminder/alert subsystem, escalation log, packaging. | `config.py`, `.env.example`, `src/memory.py`, `src/reminders.py`, `requirements.txt`, `README.md` |

> Mental model: **Scope** defines the rules, **Harness** plays the game,
> **Instrumentation** records the replay, **Productionize** keeps it alive in prod.

### Layer detail

**SCOPE**
- `src/schema.py` — `AgentResponse` is the structured contract the model must emit
  (answer, escalated, fact/preference learned, reminder, sources, confidence, needs_human).
- `src/tools.py` — 21 tools (>16 required). Each tool's docstring *is* its scope
  description for the model. Categories: knowledge retrieval, memory, reminders,
  notes, reasoning (calculate/summarize/time), injection detection, escalation, introspection.
- `src/guardrails.py` — regex rules that block prompt injection / jailbreaks / dangerous payloads.
- `src/document_loader.py` + `src/chunker.py` — define *what* becomes knowledge (markdown → chunks).

**HARNESS**
- `src/agent.py` — the ReAct loop. Binds the 21 tools, runs up to `MAX_AGENT_STEPS=5`
  steps, supports **chaining** (multiple tool calls per step, tool outputs feed the next
  step), then forces a **structured output** via `with_structured_output(AgentResponse)`.
- `src/embedder.py` — hybrid search (Pinecone semantic + in-memory BM25 keyword), deterministic
  chunk IDs (idempotent re-ingest), plus `semantic_search`, `list_documents`, `get_document`.
- `src/knowledge_base.py` — ingest orchestration into the **new** index `madhan-week6-kb`.
- `src/escalation.py` — loop/threshold logic that escalates to **Madhan** and writes `escalations.jsonl`.

**INSTRUMENTATION**
- `src/logger.py` — writes a **separate JSON file per turn** (`logs/session_<id>/turn_NNN.json`)
  *and* a combined `session.jsonl`; also logs guardrail, search, tool-call and escalation events.
- `src/runtime.py` — `contextvars` holding the active `session_id` and escalation flag so tools
  can log/escalate correctly without the model passing session ids around.

**PRODUCTIONIZE**
- `config.py` / `.env.example` — all secrets & tunables externalized.
- `src/memory.py` — JSON-backed memory that survives restarts (facts, preferences, history).
- `src/reminders.py` — reminder/alert store surfaced to Madhan each run.
- `escalations.jsonl` + `notes.json` — durable artifacts for audit/alerting.

---

## Requirements coverage (your spec)

| Requirement | Where |
|-------------|-------|
| Read `docs/`, chunk, embed in Pinecone | `document_loader.py`, `chunker.py`, `embedder.py`, `knowledge_base.py` |
| **New** index | `config.PINECONE_INDEX_NAME = "madhan-week6-kb"` |
| Hybrid search (vector + keyword) | `embedder.hybrid_search` (Pinecone + BM25) |
| Loops + escalation to Madhan himself | `agent.py` ReAct loop + `escalation.py` (`ESCALATION_CONTACT="madhan"`) |
| Memory across runs | `memory.py` |
| Guardrails / stop prompt injection | `guardrails.py` + `detect_prompt_injection_tool` + untrusted-data rule in prompt |
| Separate log file per turn per session | `logger.log_turn` → `logs/session_<id>/turn_NNN.json` |
| Reminder section to alert Madhan | `reminders.py` + `set_reminder_tool` |
| Structured output from the model | `schema.AgentResponse` + `llm.with_structured_output` |
| 16+ tools with chaining, max steps = 5 | `tools.ALL_TOOLS` (21 tools), `agent.py` loop, `MAX_AGENT_STEPS=5` |

---

## Setup

```bash
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill PINECONE_API_KEY, OPENAI_API_KEY, GROQ_API_KEY
```

### Embedding provider (free option)

By default embeddings use OpenAI (`EMBEDDING_PROVIDER=openai`, `text-embedding-3-small`,
1536-dim). If you want a **free, offline** option with no OpenAI credits, set
`EMBEDDING_PROVIDER=local` in `.env` and install the optional deps:

```bash
pip install -r requirements-local.txt
```

Local embeddings use `all-MiniLM-L6-v2` (384-dim), so you must point at a **384-dim
Pinecone index** — set `PINECONE_INDEX_NAME=madhan-week6-kb-local` and `EMBED_DIM=384`
(or delete the old index) so the index dimension matches.


## Usage

**Console (chat in the terminal):**
```bash
python main.py
```
Commands inside the REPL: `/remind <msg>`, `/history`, `/reminders`, `quit`.

**Web interface (chat in a browser):**
```bash
D:\madhan\project\maddy\venv\Scripts\python.exe -m uvicorn app:app --reload
```
Then open http://127.0.0.1:8000 in your browser. API: `POST /api/chat` with
`{"message": "..."}`.

**Re-ingest the knowledge base (after editing `docs/`):**
```bash
python ingest.py            # add/update chunks
python ingest.py --fresh    # wipe all vectors, then re-embed exactly your docs
```

On first run the agent creates the new Pinecone index (default `madhan-week6-kb`),
embeds every markdown file under `docs/`, and builds the BM25 keyword index in memory.

## Tools available to the agent (21)

knowledge_search · semantic_search_tool · keyword_search_tool · list_documents_tool ·
get_document_tool · recall_memory · store_fact_tool · store_preference_tool ·
set_reminder_tool · list_reminders_tool · acknowledge_reminder_tool · save_note_tool ·
list_notes_tool · calculate_tool · get_current_time_tool · summarize_tool ·
detect_prompt_injection_tool · escalate_to_owner_tool · list_sessions_tool ·
read_session_turn_tool · agent_status_tool

## Project structure

```
madhan-support-agent/
├── docs/                  # markdown knowledge base (embedded into Pinecone)
├── logs/                  # session_<id>/turn_NNN.json  (per-turn files) + session.jsonl
├── src/
│   ├── agent.py           # HARNESS: ReAct loop, max 5 steps, chaining, structured output
│   ├── schema.py          # SCOPE:  structured-output contract (AgentResponse)
│   ├── tools.py           # SCOPE:   21 tools the model can call
│   ├── guardrails.py      # SCOPE:   prompt-injection defence
│   ├── document_loader.py # SCOPE:   markdown -> Documents
│   ├── chunker.py         # SCOPE:   chunking
│   ├── embedder.py        # HARNESS: hybrid (Pinecone + BM25) retrieval
│   ├── knowledge_base.py  # HARNESS: ingest into new Pinecone index
│   ├── escalation.py      # HARNESS: loop/threshold -> escalate to Madhan
│   ├── logger.py          # INSTRUMENTATION: per-turn + session logs
│   ├── runtime.py         # INSTRUMENTATION: session/escalation context
│   ├── memory.py          # PRODUCTIONIZE: cross-run memory
│   └── reminders.py       # PRODUCTIONIZE: reminder/alert subsystem
├── config.py              # PRODUCTIONIZE: externalized config
├── main.py                # entry point / REPL
└── .env.example
```
