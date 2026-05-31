"""Dynamic YAML agent loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from config import settings


REQUIRED_FIELDS = {
    "name",
    "description",
    "system_prompt",
    "tools",
    "model",
    "temperature",
    "dependencies",
    "triggers",
}


def _safe_load_yaml(path: Path) -> Dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}
    return raw if isinstance(raw, dict) else {"_error": "YAML root must be a mapping."}


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _normalize_model(value: Any) -> Dict[str, str]:
    if isinstance(value, dict):
        provider = str(value.get("provider") or "gemini").strip() or "gemini"
        name = str(value.get("name") or settings.DEFAULT_MODEL).strip() or settings.DEFAULT_MODEL
        return {"provider": provider, "name": name}
    if isinstance(value, str) and value.strip():
        return {"provider": "gemini", "name": value.strip()}
    return {"provider": "gemini", "name": settings.DEFAULT_MODEL}


def _read_markdown(agent_name: str) -> str:
    md_path = settings.SKILLS_DIR / agent_name / "SKILL.md"
    try:
        return md_path.read_text(encoding="utf-8")
    except Exception:
        return ""


def validate_agent_config(config: Dict[str, Any], path: Path) -> Dict[str, Any]:
    normalized = dict(config)
    normalized.setdefault("name", path.stem.replace("_agent", ""))
    normalized.setdefault("description", "")
    normalized.setdefault("system_prompt", "")
    normalized["tools"] = _normalize_list(normalized.get("tools"))
    normalized["dependencies"] = _normalize_list(normalized.get("dependencies"))
    normalized["triggers"] = [term.lower() for term in _normalize_list(normalized.get("triggers"))]
    normalized["model"] = _normalize_model(normalized.get("model"))
    normalized["temperature"] = float(normalized.get("temperature", 0.1) or 0.1)
    normalized["yaml_path"] = str(path)
    normalized["documentation"] = _read_markdown(normalized["name"])
    normalized["skill_doc_path"] = str(settings.SKILLS_DIR / normalized["name"] / "SKILL.md")

    missing = sorted(field for field in REQUIRED_FIELDS if field not in config)
    normalized["validation_errors"] = []
    if missing:
        normalized["validation_errors"].append(
            f"Missing required field(s): {', '.join(missing)}"
        )
    if not normalized["system_prompt"]:
        normalized["validation_errors"].append("system_prompt is empty.")
    return normalized


def load_agent(path: Path) -> Optional[Dict[str, Any]]:
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return None
    data = _safe_load_yaml(path)
    if not data:
        return None
    return validate_agent_config(data, path)


def load_all_agents(agents_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    base = Path(agents_dir) if agents_dir else settings.AGENTS_DIR
    catalog: Dict[str, Dict[str, Any]] = {}
    if not base.exists():
        return catalog

    for path in sorted(base.glob("*.yaml")):
        agent = load_agent(path)
        if agent is None:
            continue
        if agent["name"] == "supervisor":
            continue
        catalog[agent["name"]] = agent
    for path in sorted(base.glob("*.yml")):
        agent = load_agent(path)
        if agent is None:
            continue
        if agent["name"] == "supervisor":
            continue
        catalog[agent["name"]] = agent
    return catalog
