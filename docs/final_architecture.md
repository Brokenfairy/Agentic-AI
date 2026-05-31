# SkillFlow AI Final Architecture

## System Architecture

SkillFlow AI Phase 5 is structured as a modular orchestration platform with a shared workflow model across UI, backend, replay, persistence, and exports.

Core layers:

- planning and supervision
- execution and collaboration
- persistence and replay
- UI and API
- exports and observability

## Workflow Lifecycle

1. Query enters the planner.
2. Query understanding normalizes the request.
3. The autonomous supervisor produces a workflow plan.
4. Dependencies are resolved into execution order.
5. URL discovery runs.
6. Page reading runs with retries and checkpoints.
7. Extraction agents run in parallel.
8. Collaboration memory captures intermediate outputs and validation requests.
9. Aggregation and comparison produce ranked outputs.
10. Exports, traces, checkpoints, and database records are persisted.

## Supervisor Orchestration

- `core/planner.py` generates the plan.
- `core/deep_supervisor.py` applies the plan, tools, templates, and marketplace packs.
- fallback heuristic planning remains available when Gemini is unavailable.

## Skill System

- skills remain YAML-driven
- agents remain YAML-driven
- templates influence plan construction
- marketplace packs provide discoverable domain groupings

## Agent Collaboration

- `core/agent_collaboration.py` provides shared memory and validation requests
- extraction agents can publish outputs and ask peers for validation context

## Persistence Layer

- SQLite in `database/db.py`
- workflow runs, summaries, trace snippets, export paths, and selected skills are stored automatically

## Observability

- Langfuse spans
- local JSON traces
- checkpoint trail
- retry tracking
- live supervisor thoughts
- dependency graph

## Replay System

- trace replay from JSON
- run replay from SQLite
- history UI and backend endpoints use the same replay helpers

## Backend

- FastAPI app under `backend/`
- routes for run, history, replay, and export retrieval

## Production-Style Patterns

- modular directories
- isolated persistence layer
- explicit retry and recovery engine
- export abstraction
- tool metadata registry
- autonomous planning + fallback behavior
