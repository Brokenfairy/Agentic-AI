"""CLI entry point for SkillFlow AI Phase 5."""

from __future__ import annotations

import argparse
import json
import sys

from core.agent_loader import load_all_agents
from core.supervisor import run_supervisor
from core.workflow_executor import run_workflow
from core.workflow_replay import replay_trace
from core.workflow_state import new_state


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SkillFlow AI workflow on a query.")
    parser.add_argument("query", nargs="*", help="The user query.")
    parser.add_argument("--json", action="store_true", help="Print the full workflow state as JSON.")
    parser.add_argument("--plan-only", action="store_true", help="Run only query parsing and autonomous planning.")
    parser.add_argument("--graph", action="store_true", help="Run via the LangGraph wrapper.")
    parser.add_argument("--replay", help="Replay a saved workflow trace JSON file.")
    parser.add_argument("--replay-db", type=int, help="Replay a stored database workflow run by id.")
    parser.add_argument("--no-compare", action="store_true", help="Disable heuristic vs Gemini compare mode.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    if args.replay:
        payload = replay_trace(args.replay)
        print(json.dumps(payload, indent=2, default=str) if args.json else payload.get("summary_markdown", ""))
        return 0
    if args.replay_db is not None:
        payload = replay_trace(str(args.replay_db), source="database")
        print(json.dumps(payload, indent=2, default=str) if args.json else payload.get("summary_markdown", ""))
        return 0

    query = " ".join(args.query).strip() or input("Enter a query: ").strip()
    if not query:
        print("No query provided. Exiting.", file=sys.stderr)
        return 1

    if not load_all_agents():
        print("No agent YAML files found under agents/. Aborting.", file=sys.stderr)
        return 2

    if args.plan_only:
        state = new_state(query)
        run_supervisor(state)
        print(f"Supervisor backend: {state.supervisor_backend}")
        print(f"Plan goal: {state.plan_goal}")
        print(f"Plan steps: {state.plan_steps}")
        print(f"Selected: {state.selected_skills}")
        if args.json:
            print(json.dumps(state.to_dict(), indent=2, default=str))
        return 0

    if args.graph:
        from workflow.graph import run_graph

        state = run_graph(query)
    else:
        state = run_workflow(query, enable_compare=not args.no_compare)

    summary = (state.aggregated_results or {}).get("summary") or {}
    rows = (state.aggregated_results or {}).get("rows") or []

    print(f"\n{'=' * 60}")
    print("  WORKFLOW RESULTS")
    print(f"{'=' * 60}")
    print(f"Trace ID:            {state.trace_id}")
    print(f"Trace Path:          {state.trace_path}")
    print(f"DB Run ID:           {state.db_run_id}")
    print(f"Supervisor Backend:  {state.supervisor_backend}")
    print(f"Plan Goal:           {state.plan_goal}")
    print(f"Selected Skills:     {', '.join(state.selected_skills or [])}")
    print(f"URLs Found:          {summary.get('total_urls', 0)}")
    print(f"Successful:          {summary.get('success_count', 0)}")
    print(f"Fallback Rows:       {summary.get('fallback_count', 0)}")
    print(f"Failed Reads:        {summary.get('failed_count', 0)}")
    print(f"Exports:             {state.export_paths}")

    if rows:
        print(f"\n{'=' * 60}")
        print("  EXTRACTED DATA")
        print(f"{'=' * 60}")
        headers = list(rows[0].keys())
        col_widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers}

        header_line = " | ".join(h.upper().ljust(col_widths[h]) for h in headers)
        print(header_line)
        print("-" * len(header_line))

        for row in rows:
            line = " | ".join(str(row.get(h, "")).ljust(col_widths[h]) for h in headers)
            print(line)
    else:
        print("\nNo extracted data rows.")

    if args.json:
        print(json.dumps(state.to_dict(), indent=2, default=str))

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
