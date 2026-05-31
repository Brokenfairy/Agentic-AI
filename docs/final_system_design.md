# Final System Design

## Architecture Overview

SkillFlow AI Phase 6 is a production-style autonomous orchestration prototype built around a Gemini-first, fallback-safe execution model.

Core layers:

- Supervisor and planner: `core/planner.py`, `core/deep_supervisor.py`
- Agents and YAML skills: `agents/`, `core/agent_loader.py`
- Tool registry: `core/tool_registry.py`
- LangGraph-style execution runtime: `core/workflow_executor.py`
- Recovery and checkpoints: `core/recovery_engine.py`, `core/checkpoints.py`, `core/failure_simulator.py`
- Persistence and replay: `database/db.py`, `core/workflow_replay.py`
- Observability and tracing: `core/logger.py`, `langfuse_config.py`
- Exports and reports: `exports/`, `reports/`
- Evaluation and benchmarks: `evals/`, `benchmarks/`
- UI and backend: `app.py`, `backend/`

## Workflow Lifecycle

1. Query enters the planner.
2. Planner builds a structured execution plan using Gemini when available, otherwise heuristics.
3. Supervisor resolves skills, dependencies, templates, marketplace packs, and available tools.
4. URL discovery and page reading execute with retries and checkpoint persistence.
5. Extraction agents run in parallel and publish intermediate outputs into collaboration memory.
6. Aggregation and comparison produce structured results.
7. Exports, reports, traces, checkpoints, and database records are persisted.
8. Replay frames and analytics are generated for observability and presentation.

## Skill and Agent System

- Skills remain YAML-driven.
- Every agent config contains description, prompt, tool bindings, dependencies, model metadata, and triggers.
- `SKILL.md` content is linked into runtime traceability.
- New agents can be added without Python routing changes.

## Observability

- Langfuse traces capture workflow-level and span-level activity.
- Local JSON traces provide deterministic replay.
- SQLite stores state snapshots, summaries, reports, and evaluation scores.
- Streamlit dashboards expose workflow health, Langfuse metrics, agent performance, and supervisor analytics.

## Reliability Model

- Failure simulation demonstrates retry and fallback behavior.
- Demo presentation mode prioritizes cache, replay, and mock-safe continuity.
- Startup checks validate required paths, templates, agent YAML, and provider readiness.
- Evaluation thresholds are configurable through `config/eval_config.yaml`.
