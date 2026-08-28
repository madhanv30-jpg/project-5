# Project Overview

Madhan's personal support agent for Week 6 (built by Karthick).

## Agent
`madhan-support-agent` — a tool-calling ReAct agent (max 5 steps, 21 tools, chaining)
with structured output, hybrid Pinecone+BM25 search, memory, guardrails, reminders, and escalation to Madhan.

## Layer map
- **Scope**: `src/schema.py`, `src/tools.py`, `src/guardrails.py`, `src/document_loader.py`, `src/chunker.py`
- **Harness**: `src/agent.py`, `src/embedder.py`, `src/knowledge_base.py`, `src/escalation.py`
- **Instrumentation**: `src/logger.py`, `src/runtime.py`
- **Productionize**: `config.py`, `src/memory.py`, `src/reminders.py`

## Run
```bash
python main.py
```
First run creates the new Pinecone index `madhan-week6-kb` and embeds `docs/`.

## Env
Copy `.env.example` to `.env` and set PINECONE_API_KEY, OPENAI_API_KEY, GROQ_API_KEY.
