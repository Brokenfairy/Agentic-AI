"""Compatibility wrapper around the Phase 5 agent loader."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core.agent_loader import load_all_agents


def load_all_skills(skills_dir: Optional[Path] = None) -> Dict[str, dict]:
    return load_all_agents(skills_dir)


def list_skill_names(skills_dir: Optional[Path] = None) -> List[str]:
    return list(load_all_agents(skills_dir).keys())
