# SkillFlow AI Architecture

Phase 5 transforms the POC into a configurable autonomous orchestration platform.

## High-Level Flow

```text
User Query
  ->
Query Understanding
  ->
Autonomous Planner
  ->
Supervisor Orchestration
  ->
Dependency Resolver
  ->
URL Discovery
  ->
Page Reader + Retry / Recovery
  ->
Parallel Extraction Agents
  ->
Collaboration Memory
  ->
Aggregation + Comparison
  ->
Multi-Format Exports
  ->
SQLite Memory + Trace Replay + Langfuse
```

## Core Modules

- `core/planner.py`: dynamic execution plans
- `core/deep_supervisor.py`: plan application and skill selection
- `core/workflow_executor.py`: end-to-end orchestration runtime
- `core/agent_collaboration.py`: shared workflow memory and validation requests
- `core/tool_registry.py`: tool discovery and metadata registry
- `core/checkpoints.py`: intermediate state persistence
- `core/recovery_engine.py`: retries and partial recovery
- `core/comparison_engine.py`: structured ranking and best-deal analysis
- `database/db.py`: workflow memory in SQLite

## Platform Surfaces

- Streamlit UI for live execution, analytics, replay, history, reasoning, and config editing
- FastAPI backend for run, history, replay, and export retrieval
- local JSON traces
- Langfuse traces when configured

## Enterprise Demo Mode

When `DEMO_PRESENTATION_MODE=true`, the platform can preload history, traces, analytics, and reports so demo sessions remain fast and stable even when live scraping is unreliable.
