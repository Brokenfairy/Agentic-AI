"""Startup validation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from config import settings
from core.agent_loader import load_all_agents
from core.llm_provider import build_llm
from core.planner import load_workflow_templates


def run_startup_checks() -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []

    checks.append({"name": "gemini_provider", "ok": build_llm() is not None or not settings.has_google(), "detail": "Gemini provider ready or heuristic fallback available."})
    checks.append({"name": "tavily_api", "ok": True, "detail": "Tavily is optional; fallback search remains available."})
    checks.append({"name": "langfuse", "ok": True, "detail": "Langfuse is optional; local traces remain available."})

    required_paths = [
        settings.OUTPUTS_DIR,
        settings.TRACES_DIR,
        settings.DEMO_CACHE_DIR,
        settings.TEMPLATES_DIR,
        settings.REPORTS_DIR,
        settings.BENCHMARKS_DIR,
        settings.DEMO_SCENARIOS_DIR,
    ]
    for path in required_paths:
        checks.append({"name": f"path:{path.name}", "ok": Path(path).exists(), "detail": str(path)})

    templates = load_workflow_templates()
    checks.append({"name": "workflow_templates", "ok": bool(templates), "detail": f"{len(templates)} template(s) discovered."})

    agents = load_all_agents()
    invalid_agents = [name for name, meta in agents.items() if meta.get("validation_errors")]
    checks.append({"name": "agent_yaml_validity", "ok": not invalid_agents, "detail": f"invalid={invalid_agents}"})

    eval_config_path = settings.BASE_DIR / "config" / "eval_config.yaml"
    try:
        eval_config = yaml.safe_load(eval_config_path.read_text(encoding="utf-8")) or {}
        checks.append({"name": "eval_config", "ok": isinstance(eval_config, dict) and bool(eval_config), "detail": str(eval_config_path)})
    except Exception as exc:
        checks.append({"name": "eval_config", "ok": False, "detail": str(exc)})

    overall = all(item["ok"] for item in checks)
    return {"ok": overall, "checks": checks}
