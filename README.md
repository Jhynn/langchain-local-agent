# Local Multi-Framework AI Agent (LangGraph & Google ADK)

A fully local, platform-agnostic AI agent system demonstrating modern agentic patterns using both **LangGraph** and **Google ADK (Agent Development Kit)**. Powered locally via **Ollama**, the application integrates structured SQL database querying (MariaDB + Peewee ORM), persistent conversation checkpointing, a typed CLI (Typer), and a REST API (FastAPI).

## Architecture Overview

This repository contrasts and combines three production-ready agentic orchestration patterns over a shared layer of typed Python tools and relational data:

1. **LangGraph ReAct Agent (`app/agents/assistant_agent.py`):**
   * Implements a stateful ReAct (Reason + Act) loop using `langgraph.prebuilt.create_react_agent`.
   * Persists multi-turn conversation state across process restarts via `SqliteSaver` indexed by `thread_id`.
2. **Google ADK Dynamic Multi-Agent Router (`app/agents/adk_agent.py`):**
   * Uses a root coordinator agent (`corporate_coordinator`) that delegates tasks dynamically to specialist sub-agents (`financial_analyst` and `system_utility`) via `transfer_to_agent`.
   * Connects to local Ollama models through LiteLLM (`ollama_chat/`).
3. **Google ADK Deterministic Workflow (`app/agents/adk_workflow.py`):**
   * Combines `ParallelAgent` and `SequentialAgent` into a predictable two-stage audit pipeline.
   * Executes concurrent data collection (`financial_collector` and `system_collector`), writes outputs to `session.state` via `output_key`, and synthesizes a final structured report without routing overhead.

## Key Features

* **100% Local Execution:** Zero external API keys required; runs locally via Ollama (`llama3.2`).
* **Database Integration & Guardrails:** Connects to MariaDB using Peewee ORM for structured queries, alongside a read-only SQL execution tool that blocks destructive DDL/DML statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).
* **Persistent Session Memory:** Disk-backed SQLite checkpointing for LangGraph threads and session-managed state for Google ADK.
* **Dual Interface:** Expose capabilities both through a typed **Typer CLI** and an asynchronous **FastAPI** web service with latency telemetry middleware.
* **Strict Static Typing:** End-to-end Python type hints across models, schemas, tools, agents, and endpoints.

## Tech Stack

* **Agent Frameworks:** LangGraph, LangChain, Google ADK, LiteLLM
* **Local LLM Runtime:** Ollama (`llama3.2`)
* **Web Framework:** FastAPI + Uvicorn
* **CLI Framework:** Typer
* **Database & ORM:** MariaDB + Peewee + PyMySQL
* **Checkpointing:** SQLite (`langgraph-checkpoint-sqlite`)
* **Validation & Config:** Pydantic + Pydantic Settings
* **Observability:** Loguru
* **Package Manager:** uv

## Prerequisites

* Python 3.12+
* [uv](https://github.com/astral-sh/uv) installed
* MariaDB server running locally
* [Ollama](https://ollama.com/) running locally with the `llama3.2` model pulled:
  ```bash
  ollama pull llama3.2
  ```

## Setup and Installation

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Create the MariaDB database:**
   ```sql
   CREATE DATABASE IF NOT EXISTS agent_corporate_db;
   ```

3. **Configure environment variables:**
   Create a `.env` file in the project root (do not wrap values in quotes):
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   LLM_MODEL=llama3.2
   LLM_TEMPERATURE=0.0

   DB_USER=root
   DB_PASSWORD=your_password
   DB_HOST=127.0.0.1
   DB_PORT=3306
   DB_NAME=agent_corporate_db

   CHECKPOINT_DB_PATH=./agent_checkpoints.db
   ```
   *Note: On first startup, the application automatically creates the `expenses` table and seeds sample corporate expense records if the table is empty.*

## Usage Examples

### 1. Typer CLI Usage

Inspect available subcommands and options:
```bash
uv run python -m app.cli --help
```

#### LangGraph Agent (Persistent SQLite Memory)

Ask a single question and persist the session state to SQLite:
```bash
uv run python -m app.cli ask "Which expenses are currently pending approval?" --session-id audit-01
```

Follow up in a separate process execution using the same `--session-id` (demonstrating disk-backed memory):
```bash
uv run python -m app.cli ask "What is the combined total of those pending expenses?" --session-id audit-01
```

Inspect the persisted conversation history for a session:
```bash
uv run python -m app.cli history --session-id audit-01
```

Start an interactive multi-turn terminal chat:
```bash
uv run python -m app.cli chat --session-id audit-01
```

#### Google ADK Multi-Agent & Deterministic Workflow

Start an interactive session with the ADK dynamic multi-agent coordinator:
```bash
uv run python -m app.cli adk-chat --session-id adk-session-01
```

Run the deterministic `ParallelAgent -> SequentialAgent` audit pipeline:
```bash
uv run python -m app.cli adk-audit --scope "Audit all corporate expenses by department and list pending approvals."
```

### 2. FastAPI REST API Usage

Start the FastAPI server:
```bash
uv run uvicorn app.main:app --reload
```

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.

#### Query the LangGraph ReAct Agent
```bash
curl -X POST "http://127.0.0.1:8000/api/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "web-session-01",
    "message": "Give me a spending breakdown by department."
  }'
```

Retrieve persisted LangGraph thread history:
```bash
curl -X GET "http://127.0.0.1:8000/api/chat/web-session-01/history"
```

#### Query the Google ADK Multi-Agent Router
```bash
curl -X POST "http://127.0.0.1:8000/api/adk/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "adk-web-01",
    "message": "Who spent the highest single amount in the expenses database?"
  }'
```

#### Trigger the Google ADK Deterministic Audit Pipeline
```bash
curl -X POST "http://127.0.0.1:8000/api/adk/chat/audit" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "audit-run-01",
    "scope": "Generate a complete corporate expense audit report covering department totals and pending approvals."
  }'
```

## Project Structure

```text
langchain-local-agent/
├── app/
│   ├── agents/
│   │   ├── assistant_agent.py   # LangGraph ReAct agent + SqliteSaver
│   │   ├── adk_agent.py         # Google ADK dynamic multi-agent router
│   │   └── adk_workflow.py      # Google ADK deterministic Parallel + Sequential pipeline
│   ├── api/
│   │   └── endpoints/
│   │       ├── chat.py          # LangGraph FastAPI endpoints (/api/chat)
│   │       └── adk_chat.py      # Google ADK FastAPI endpoints (/api/adk/chat)
│   ├── core/
│   │   ├── config.py            # Typed environment settings
│   │   ├── database.py          # MariaDB connection & initial seed
│   │   └── logger.py            # Loguru structured logging configuration
│   ├── models/
│   │   └── expense.py           # Peewee ORM model
│   ├── schemas/
│   │   └── chat.py              # Pydantic request/response DTOs
│   ├── tools/
│   │   ├── db_tools.py          # MariaDB ORM & read-only SQL tools
│   │   ├── system_tools.py      # OS & datetime utilities
│   │   └── text_tools.py        # Text metric utilities
│   ├── cli.py                   # Typer CLI entry point
│   └── main.py                  # FastAPI entry point (lifespan + telemetry)
├── .env
├── .gitignore
├── pyproject.toml
└── README.md
```
