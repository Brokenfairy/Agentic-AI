"""
Test UI smoke checks.

Validates:
- app imports successfully
- main components load
- no missing imports
- no missing files
- default demo query exists
- outputs folder exists

No browser automation required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest


class TestUISmoke:
    """Test UI smoke checks without browser automation."""

    def test_app_imports_successfully(self) -> None:
        """Test that app.py can be imported."""
        try:
            import app
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import app: {e}")

    def test_streamlit_import_available(self) -> None:
        """Test that streamlit is available."""
        try:
            import streamlit as st
            assert True
        except ImportError:
            pytest.fail("streamlit not installed")

    def test_components_import_successfully(self) -> None:
        """Test that all components can be imported."""
        try:
            from components import (
                render_execution_timeline,
                render_observability_panel,
                render_skill_cards,
                render_workflow_graph,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import components: {e}")

    def test_workflow_visualizer_import(self) -> None:
        """Test that workflow visualizer can be imported."""
        try:
            from components.workflow_visualizer import (
                build_workflow_dot,
                render_workflow_graph,
            )
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import workflow_visualizer: {e}")

    def test_execution_timeline_import(self) -> None:
        """Test that execution timeline can be imported."""
        try:
            from components.execution_timeline import render_execution_timeline
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import execution_timeline: {e}")

    def test_skill_cards_import(self) -> None:
        """Test that skill cards can be imported."""
        try:
            from components.skill_cards import render_skill_cards
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import skill_cards: {e}")

    def test_observability_panel_import(self) -> None:
        """Test that observability panel can be imported."""
        try:
            from components.observability_panel import render_observability_panel
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import observability_panel: {e}")

    def test_core_modules_import(self) -> None:
        """Test that all core modules can be imported."""
        core_modules = [
            "core.workflow_executor",
            "core.workflow_state",
            "core.query_parser",
            "core.supervisor",
            "core.extractor_engine",
            "core.result_aggregator",
            "core.skill_loader",
            "core.logger",
        ]
        
        for module_name in core_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_tools_modules_import(self) -> None:
        """Test that all tool modules can be imported."""
        tool_modules = [
            "tools.web_search_tool",
            "tools.page_reader",
            "tools.excel_writer_tool",
        ]
        
        for module_name in tool_modules:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_outputs_folder_exists(self) -> None:
        """Test that outputs folder exists or can be created."""
        project_root = Path(__file__).parent.parent
        outputs_dir = project_root / "outputs"
        
        # Folder should exist or be creatable
        if not outputs_dir.exists():
            outputs_dir.mkdir(exist_ok=True)
        
        assert outputs_dir.exists()
        assert outputs_dir.is_dir()

    def test_traces_folder_exists(self) -> None:
        """Test that traces folder exists or can be created."""
        project_root = Path(__file__).parent.parent
        traces_dir = project_root / "traces"
        
        if not traces_dir.exists():
            traces_dir.mkdir(exist_ok=True)
        
        assert traces_dir.exists()

    def test_skills_folder_exists(self) -> None:
        """Test that skills folder exists."""
        project_root = Path(__file__).parent.parent
        skills_dir = project_root / "skills"
        
        assert skills_dir.exists()
        assert skills_dir.is_dir()

    def test_agents_folder_exists(self) -> None:
        """Test that agents folder exists."""
        project_root = Path(__file__).parent.parent
        agents_dir = project_root / "agents"
        
        assert agents_dir.exists()
        assert agents_dir.is_dir()

    def test_env_example_exists(self) -> None:
        """Test that .env.example exists."""
        project_root = Path(__file__).parent.parent
        env_example = project_root / ".env.example"
        
        assert env_example.exists()

    def test_requirements_txt_exists(self) -> None:
        """Test that requirements.txt exists."""
        project_root = Path(__file__).parent.parent
        requirements = project_root / "requirements.txt"
        
        assert requirements.exists()

    def test_config_folder_exists(self) -> None:
        """Test that config folder exists."""
        project_root = Path(__file__).parent.parent
        config_dir = project_root / "config"
        
        assert config_dir.exists()

    def test_demo_queries_defined(self) -> None:
        """Test that demo queries are defined in app.py."""
        import app
        
        # Check for DEMO_QUERIES constant
        assert hasattr(app, "DEMO_QUERIES")
        assert isinstance(app.DEMO_QUERIES, list)
        assert len(app.DEMO_QUERIES) > 0

    def test_main_py_imports(self) -> None:
        """Test that main.py can be imported."""
        try:
            import main
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import main: {e}")

    def test_langfuse_config_import(self) -> None:
        """Test that langfuse_config can be imported."""
        try:
            import langfuse_config
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import langfuse_config: {e}")

    def test_schemas_import(self) -> None:
        """Test that schemas can be imported."""
        try:
            from schemas import SemanticExtractionResult, WorkflowSummary
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import schemas: {e}")

    def test_no_missing_core_files(self) -> None:
        """Test that all expected core files exist."""
        project_root = Path(__file__).parent.parent
        
        required_files = [
            "app.py",
            "main.py",
            "requirements.txt",
            ".env.example",
            "core/__init__.py",
            "core/workflow_executor.py",
            "core/workflow_state.py",
            "tools/__init__.py",
            "components/__init__.py",
        ]
        
        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Missing required file: {file_path}"

    def test_config_settings_import(self) -> None:
        """Test that config.settings can be imported."""
        try:
            from config import settings
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import config.settings: {e}")

    def test_demo_mode_import(self) -> None:
        """Test that demo_mode can be imported."""
        try:
            from config import demo_mode
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import demo_mode: {e}")
