"""Autonomous planning engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from config import settings
from core.failure_simulator import maybe_raise
from core.agent_loader import load_all_agents
from core.llm_provider import build_llm
from core.query_parser import parse_query
from schemas import ExecutionPlanSchema


STEP_LIBRARY = {
    "url_scraper": "discover_urls",
    "price_extractor": "extract_prices",
    "rating_extractor": "extract_ratings",
    "availability_extractor": "extract_availability",
    "specs_extractor": "extract_specifications",
    "location_extractor": "extract_locations",
    "comparison_engine": "compare_results",
    "excel_writer": "generate_report",
}


def load_workflow_templates() -> List[Dict[str, Any]]:
    templates: List[Dict[str, Any]] = []
    for path in sorted(settings.TEMPLATES_DIR.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if isinstance(raw, dict):
            raw["path"] = str(path)
            raw["name"] = raw.get("name") or path.stem
            templates.append(raw)
    return templates


def _template_matches(query: str, template: Dict[str, Any]) -> bool:
    lowered = query.lower()
    for term in template.get("match_terms") or []:
        if str(term).lower() in lowered:
            return True
    return False


def _select_template(query: str, templates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for template in templates:
        if _template_matches(query, template):
            return template
    return None


def _extract_json(text: str) -> Dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        return {}


def _heuristic_plan(
    query: str,
    parsed_query: Dict[str, Any],
    catalog: Dict[str, Dict[str, Any]],
    selected_template: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    requested_fields = set(parsed_query.get("requested_fields") or [])
    required_skills = ["query_understanding", "url_scraper"]
    reasoning = [
        "Start with query understanding to normalize the request.",
        "Discover candidate URLs before any extraction agents run.",
    ]

    for skill_name in catalog:
        if skill_name in {"query_understanding", "url_scraper", "excel_writer"}:
            continue
        triggers = set(catalog[skill_name].get("triggers") or [])
        if requested_fields.intersection(triggers) or any(field in skill_name for field in requested_fields):
            required_skills.append(skill_name)
            reasoning.append(f"Added {skill_name} because it matches requested fields {sorted(requested_fields)}.")

    if any(word in query.lower() for word in ("compare", "best", "lowest", "highest", "rank")):
        required_skills.append("comparison_engine")
        reasoning.append("Added comparison_engine because the query implies ranking or comparison.")

    if selected_template:
        for skill in selected_template.get("required_skills") or []:
            if skill not in required_skills:
                required_skills.append(skill)
        reasoning.append(f"Matched workflow template '{selected_template.get('name')}'.")

    if "excel_writer" not in required_skills:
        required_skills.append("excel_writer")

    steps = [STEP_LIBRARY.get(skill, skill) for skill in required_skills]
    goal = parsed_query.get("search_query") or query
    return {
        "goal": f"Execute workflow for: {goal}",
        "steps": steps,
        "required_skills": required_skills,
        "reasoning": reasoning,
        "template": (selected_template or {}).get("name"),
    }


def _llm_plan(
    query: str,
    parsed_query: Dict[str, Any],
    catalog: Dict[str, Dict[str, Any]],
    templates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    llm = build_llm()
    if llm is None:
        return {}

    agent_summaries = {
        name: {
            "description": meta.get("description", ""),
            "dependencies": meta.get("dependencies", []),
            "triggers": meta.get("triggers", []),
        }
        for name, meta in catalog.items()
    }
    template_summaries = [
        {
            "name": template.get("name"),
            "description": template.get("description", ""),
            "required_skills": template.get("required_skills", []),
            "match_terms": template.get("match_terms", []),
        }
        for template in templates
    ]

    prompt = (
        "You are an autonomous workflow planner for SkillFlow AI.\n"
        "Generate a JSON execution plan with keys goal, steps, required_skills, reasoning, template.\n"
        "Always include query_understanding, url_scraper, and excel_writer.\n"
        "Add comparison_engine when ranking, comparison, best-deal, or price-difference analysis is implied.\n"
        "Use only skills present in the agent catalog.\n\n"
        f"Query: {query}\n"
        f"Parsed Query: {json.dumps(parsed_query, indent=2)}\n"
        f"Agent Catalog: {json.dumps(agent_summaries, indent=2)}\n"
        f"Templates: {json.dumps(template_summaries, indent=2)}\n"
        "Return JSON only."
    )
    try:
        maybe_raise("gemini")
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)
        plan = _extract_json(str(content))
        if plan:
            return plan
    except Exception:
        return {}
    return {}


def generate_execution_plan(query: str) -> Dict[str, Any]:
    catalog = load_all_agents()
    parsed_query = parse_query(query)
    templates = load_workflow_templates()
    selected_template = _select_template(query, templates)

    plan = _llm_plan(query, parsed_query, catalog, templates) if settings.has_google() else {}
    if not plan:
        plan = _heuristic_plan(query, parsed_query, catalog, selected_template)

    validated = ExecutionPlanSchema(**plan)
    return validated.model_dump() if hasattr(validated, "model_dump") else validated.dict()
