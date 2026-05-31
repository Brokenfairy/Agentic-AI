# SkillFlow AI

SkillFlow AI Phase 6 is a Gemini-first autonomous orchestration platform prototype focused on evaluation, reliability, observability, replay, and demo-safe packaging.

## What It Demonstrates

- autonomous planning with Gemini plus heuristic fallback
- YAML-driven skill selection and dependency-aware orchestration
- multi-agent extraction with shared workflow memory
- LangGraph-style staged execution with retries, checkpoints, and replay frames
- Langfuse tracing plus local trace persistence
- SQLite workflow memory and analytics
- semantic extraction, comparison, and multi-format exports
- evaluation harness, reliability scoring, reports, and benchmarks
- enterprise-style Streamlit dashboard and FastAPI backend

## Core Architecture

- `core/planner.py`: execution plan generation
- `core/deep_supervisor.py`: autonomous supervisor and skill orchestration
- `core/workflow_executor.py`: runtime execution, persistence, exports, replay frames
- `core/tool_registry.py`: dynamic tool discovery
- `core/failure_simulator.py`: failure injection for reliability demos
- `database/db.py`: workflow persistence and analytics
- `evals/`: golden cases, scoring, reliability, reports
- `reports/`: workflow, extraction quality, reliability reports
- `benchmarks/`: performance measurements
- `components/`: observability, health, Langfuse, history, analytics, presentation dashboard

## Setup

```bash
pip install -r requirements.txt
playwright install
```

Copy `.env.example` to `.env` and configure what you have available.

### Gemini

```bash
GOOGLE_API_KEY=
DEFAULT_MODEL=gemini-2.0-flash
FALLBACK_GEMINI_MODEL=gemini-1.5-flash
```

Without `GOOGLE_API_KEY`, the platform remains functional in heuristic mode.

### Optional Services

```bash
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
TAVILY_API_KEY=
```

## Demo Mode

```bash
DEMO_MODE=true
DEMO_PRESENTATION_MODE=true
```

Presentation mode preloads history, cached URLs, replayable traces, reports, and fallback-safe workflow paths so the demo does not fully fail.

## Run

### One-click demo

```bash
python demo_runner.py
```

### Streamlit UI

```bash
streamlit run app.py
```

### CLI

```bash
python main.py "Compare iPhone 15 prices across websites and rank the best deal"
python main.py --plan-only "Find top 5 restaurants in Bangalore and compare rating and location"
python main.py --replay traces/example.json
python main.py --replay-db 2
```

### Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Evaluation Flow

```bash
python evals/runner.py
```

Outputs:

- `evals/reports/*.json`
- `evals/reports/*.md`

Configuration:

- `config/eval_config.yaml`

The eval harness measures skill precision, skill recall, workflow reliability, extraction quality, fallback usage, and completion stability across 15 golden cases.

## Replay System

- JSON traces are stored in `traces/`
- workflow state snapshots are stored in SQLite
- replay frames are persisted in the state payload
- the UI can load replayable database runs or trace files

## Reporting and Benchmarks

```bash
python benchmarks/runner.py
```

Generated assets:

- `reports/*_workflow.md`
- `reports/*_extraction_quality.md`
- `reports/*_reliability.md`
- `reports/*_pdf_ready.md`
- `benchmarks/benchmark_results.json`

## Testing

### Quick Validation

Run the final readiness check to verify system health:

```bash
python final_check.py
```

Expected output:
```
SkillFlow AI Final Readiness Report

✅ Environment loaded
✅ Skills valid
✅ Supervisor working
...
Final Readiness Score: 95/100
```

### Full Test Suite

Run the complete pytest suite:

```bash
pytest tests/ -v
```

Test categories:
- `test_skill_loader.py` - YAML skill validation
- `test_query_parser.py` - Query parsing
- `test_supervisor_selection.py` - Skill selection logic
- `test_url_scraper.py` - URL discovery (mocked)
- `test_page_reader.py` - Page reading (mocked)
- `test_extractor_engine.py` - Field extraction
- `test_excel_export.py` - Excel generation
- `test_langfuse_integration.py` - Tracing (mocked)
- `test_workflow_executor.py` - End-to-end workflow
- `test_replay_system.py` - Workflow replay
- `test_ui_smoke.py` - UI component imports

All tests run without API keys using mocked services.

### Demo Mode Testing

Test with guaranteed stability:

```bash
# Set demo mode
export DEMO_MODE=true

# Run quick test
python -c "from core.workflow_executor import run_workflow; s = run_workflow('Find iPhone 15 price'); print(f'Status: {s.workflow_status}')"
```

## Final Readiness

Before presenting, ensure:

1. **System passes health check:**
   ```bash
   python final_check.py
   # Expected: Score 75+ (Good or higher)
   ```

2. **All tests pass:**
   ```bash
   pytest tests/ --tb=short
   # Expected: All tests passing
   ```

3. **Demo queries work:**
   ```bash
   python main.py "Find top 5 URLs for iPhone 15 and extract price and rating"
   ```

4. **Outputs folder exists:**
   ```bash
   mkdir -p outputs traces
   ```

See [Demo Checklist](docs/demo_checklist.md) for complete pre-demo steps.

## Final Commands Summary

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install

# 2. Validate system
python final_check.py

# 3. Run test suite
pytest tests/ -v

# 4. Start Streamlit demo
streamlit run app.py

# 5. Or run CLI
python main.py "Find iPhone 15 price"

# 6. Or run backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Known Limitations

- **Query Parser**: Rule-based (not LLM-powered), may miss complex queries
- **Extraction**: Best-effort regex/heuristics, Gemini improves accuracy but requires API key
- **Page Reading**: JavaScript-heavy sites need Playwright (slower)
- **Rate Limits**: External APIs (Tavily, Gemini) may rate-limit heavy usage
- **Demo Mode**: Uses mock data for reliability, not real-time scraping
- **Skill YAML**: Manual updates required to add new field extractors

## Troubleshooting

See [Troubleshooting Guide](docs/troubleshooting.md) for detailed fixes:

- No Gemini key: falls back to heuristic extraction
- No Tavily key: uses mock/cached URLs
- No Langfuse: local traces still work
- Excel errors: check `outputs/` folder exists
- Import errors: verify all `__init__.py` files present
- Demo instability: enable `DEMO_MODE=true`

## Docs

- [Architecture](docs/architecture.md)
- [Final Architecture](docs/final_architecture.md)
- [Final System Design](docs/final_system_design.md)
- [Demo Checklist](docs/demo_checklist.md) - Pre-demo validation steps
- [Troubleshooting](docs/troubleshooting.md) - Common issues and fixes

---

**Version:** Phase 7 - Final QA, System Validation & Demo Readiness  
**Last Updated:** 2024
