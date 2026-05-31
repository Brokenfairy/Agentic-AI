"""Autonomous supervisor orchestration."""

from __future__ import annotations

from typing import Dict, List, Tuple

from config import settings
from core.agent_loader import load_all_agents
from core.dependency_resolver import resolve_execution_order
from core.marketplace_loader import load_marketplace_packs
from core.planner import generate_execution_plan, load_workflow_templates
from core.query_parser import parse_query
from core.tool_registry import discover_tools
from core.workflow_state import WorkflowState


_ALWAYS_ON = {"query_understanding", "url_scraper", "excel_writer"}


def _tokenize(query: str) -> set[str]:
    return {part.lower() for part in query.replace(",", " ").split() if part.strip()}


def _select_heuristically(
    query: str,
    parsed_query: Dict[str, object],
    catalog: Dict[str, Dict[str, object]],
) -> Tuple[List[str], List[Dict[str, str]], List[str]]:
    tokens = _tokenize(query)
    requested_fields = {str(item).lower() for item in parsed_query.get("requested_fields", [])}
    selected: List[str] = []
    skipped: List[Dict[str, str]] = []
    reasoning: List[str] = []

    for name, meta in catalog.items():
        triggers = {str(item).lower() for item in meta.get("triggers", [])}
        if name in _ALWAYS_ON:
            selected.append(name)
            reasoning.append(f"Selected {name} because it is required in every workflow.")
            continue
        if tokens.intersection(triggers) or any(field in name for field in requested_fields):
            selected.append(name)
            reasoning.append(f"Selected {name} because query intent matched its triggers.")
        else:
            skipped.append({"name": name, "reason": "No trigger or requested field matched."})

    return selected, skipped, reasoning


def run_supervisor(state: WorkflowState) -> WorkflowState:
    catalog = load_all_agents()
    state.available_agents = catalog
    state.available_tools = discover_tools()
    state.workflow_templates = load_workflow_templates()
    state.marketplace_packs = load_marketplace_packs()
    state.parsed_query = state.parsed_query or parse_query(state.original_query)

    plan = generate_execution_plan(state.original_query)
    selected = [skill for skill in plan.get("required_skills", []) if skill in catalog]
    reasoning = [str(item) for item in plan.get("reasoning", []) if str(item).strip()]
    skipped: List[Dict[str, str]] = []

    if selected:
        state.supervisor_backend = "planner"
        state.provider_name = "gemini" if settings.has_google() else "heuristic"
        state.provider_model = settings.DEFAULT_MODEL if settings.has_google() else ""
        state.heuristic_mode = not settings.has_google()
        state.plan = plan
        state.plan_goal = plan.get("goal", "")
        state.plan_steps = list(plan.get("steps", []))
        state.supervisor_thoughts = [
            f"The query requires {state.plan_goal or 'a structured workflow'}.",
            *[f"I will {step.replace('_', ' ')}." for step in state.plan_steps[:6]],
        ]
    else:
        selected, skipped, reasoning = _select_heuristically(
            state.original_query,
            state.parsed_query,
            catalog,
        )
        state.supervisor_backend = "heuristic"
        state.provider_name = "heuristic"
        state.provider_model = ""
        state.heuristic_mode = True
        state.plan = {
            "goal": state.parsed_query.get("search_query", state.original_query),
            "steps": selected,
            "required_skills": selected,
            "reasoning": reasoning,
            "template": None,
        }
        state.plan_goal = str(state.plan.get("goal", ""))
        state.plan_steps = list(state.plan.get("steps", []))
        state.supervisor_thoughts = [
            "Gemini planning was unavailable, so I fell back to heuristic planning.",
            *[f"I selected {skill} from heuristic matching." for skill in selected[:6]],
        ]

    if not skipped:
        skipped = [
            {"name": name, "reason": "Not required by the current autonomous plan."}
            for name in catalog
            if name not in selected
        ]

    for skill in ("query_understanding", "url_scraper", "excel_writer"):
        if skill in catalog and skill not in selected:
            selected.append(skill)

    if "comparison_engine" in catalog and any(word in state.original_query.lower() for word in ("compare", "best", "lowest", "highest", "rank")):
        if "comparison_engine" not in selected:
            selected.append("comparison_engine")
            reasoning.append("Selected comparison_engine because the query implies ranked comparison.")

    if "excel_writer" in selected:
        selected = [item for item in selected if item != "excel_writer"] + ["excel_writer"]

    execution_plan = resolve_execution_order(selected, catalog)
    state.execution_plan = execution_plan
    state.selected_skills = execution_plan
    state.skipped_skills = skipped
    state.supervisor_reasoning = reasoning
    state.dependency_graph = {
        name: list((catalog.get(name) or {}).get("dependencies", []))
        for name in execution_plan
    }
    return state
