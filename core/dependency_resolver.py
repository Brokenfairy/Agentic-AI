"""Dependency-aware execution order builder."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set


def resolve_execution_order(
    selected_skills: Iterable[str],
    agent_catalog: Dict[str, Dict],
) -> List[str]:
    ordered: List[str] = []
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"Cyclic dependency detected at '{name}'.")
        visiting.add(name)
        meta = agent_catalog.get(name) or {}
        for dependency in meta.get("dependencies") or []:
            if dependency in agent_catalog:
                visit(dependency)
        visiting.remove(name)
        visited.add(name)
        if name not in ordered:
            ordered.append(name)

    for skill in selected_skills:
        if skill in agent_catalog:
            visit(skill)

    return ordered
