"""Dynamic tool discovery and registry access."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List

from tools import TOOL_METADATA, TOOL_REGISTRY


_DISCOVERED = False


def discover_tools() -> Dict[str, Dict[str, Any]]:
    global _DISCOVERED
    if _DISCOVERED and TOOL_METADATA:
        return TOOL_METADATA

    import tools

    package_path = Path(tools.__file__).resolve().parent
    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"tools.{module_info.name}")

    _DISCOVERED = True
    return TOOL_METADATA


def get_tool(name: str):
    discover_tools()
    return TOOL_REGISTRY.get(name)


def get_tool_metadata(name: str) -> Dict[str, Any]:
    discover_tools()
    return TOOL_METADATA.get(name, {})


def list_tools() -> List[Dict[str, Any]]:
    discover_tools()
    return [TOOL_METADATA[name] for name in sorted(TOOL_METADATA)]
