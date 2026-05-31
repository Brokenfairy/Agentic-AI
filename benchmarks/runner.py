"""Basic workflow and replay benchmarks."""

from __future__ import annotations

import json
import time
from pathlib import Path

from config import settings
from core.recovery_engine import count_retries
from core.workflow_executor import run_workflow
from core.workflow_replay import load_trace


def main() -> int:
    queries = [
        "Compare iPhone 15 prices across websites and rank the best deal",
        "Find top 5 restaurants in Bangalore and compare rating and location",
        "Find top 5 gaming laptops under Rs 60000 and extract price, specs, discount, and warranty",
    ]
    results = []
    for query in queries:
        started = time.perf_counter()
        state = run_workflow(query, enable_compare=False)
        duration = round(time.perf_counter() - started, 3)
        replay_started = time.perf_counter()
        load_trace(state.trace_path) if state.trace_path else None
        replay_duration = round(time.perf_counter() - replay_started, 3)
        results.append(
            {
                "query": query,
                "workflow_time_seconds": duration,
                "replay_time_seconds": replay_duration,
                "retry_count": count_retries(state.retry_attempts),
                "status": state.workflow_status,
            }
        )

    settings.BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    out = settings.BENCHMARKS_DIR / "benchmark_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
