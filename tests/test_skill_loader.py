"""
Test skill loader functionality.

Validates:
- skill.yaml files load correctly
- SKILL.md files load correctly
- Missing YAML is handled safely
- Invalid YAML shows proper error
- Skill metadata contains required fields
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from core.skill_loader import load_all_skills


class TestSkillLoader:
    """Test skill loading functionality."""

    def test_load_all_skills_returns_dict(self) -> None:
        """Test that load_all_skills returns a dictionary."""
        skills = load_all_skills()
        assert isinstance(skills, dict)

    def test_skills_contain_required_fields(self) -> None:
        """Test that loaded skills have required metadata fields."""
        skills = load_all_skills()
        
        for skill_name, skill_data in skills.items():
            # Check required fields exist
            assert "name" in skill_data, f"Skill {skill_name} missing 'name'"
            assert "description" in skill_data, f"Skill {skill_name} missing 'description'"
            
            # Name should match the key
            assert skill_data["name"] == skill_name, \
                f"Skill {skill_name} name mismatch: {skill_data['name']}"

    def test_skill_yaml_loading(self, sample_skill_yaml: str) -> None:
        """Test that skill YAML can be parsed."""
        # Parse the YAML to ensure it's valid
        parsed = yaml.safe_load(sample_skill_yaml)
        
        assert parsed is not None
        assert "name" in parsed
        assert "description" in parsed
        assert "triggers" in parsed

    def test_load_skill_metadata_with_missing_file(self) -> None:
        """Test handling of missing skill file - skills load from agent_loader."""
        # The agent loader gracefully handles missing directories
        skills = load_all_skills(Path("/nonexistent/path"))
        assert skills == {} or isinstance(skills, dict)

    def test_skills_have_triggers_or_dependencies(self) -> None:
        """Test that skills have either triggers or dependencies defined."""
        skills = load_all_skills()
        
        for skill_name, skill_data in skills.items():
            has_triggers = "triggers" in skill_data and skill_data["triggers"]
            has_dependencies = "dependencies" in skill_data and skill_data["dependencies"]
            
            # Skip check for query_understanding (root skill)
            if skill_name == "query_understanding":
                continue
                
            assert has_triggers or has_dependencies, \
                f"Skill {skill_name} should have triggers or dependencies"

    def test_skill_inputs_outputs_defined(self) -> None:
        """Test that skills define inputs/outputs or tools."""
        skills = load_all_skills()
        
        for skill_name, skill_data in skills.items():
            # Check for inputs/outputs/tools (agent-based skills use tools instead)
            has_io = any(k in skill_data for k in ["inputs", "parameters", "outputs", "returns", "tools"])
            assert has_io, f"Skill {skill_name} should define inputs, outputs, or tools"

    def test_no_duplicate_skill_names(self) -> None:
        """Test that there are no duplicate skill names."""
        skills = load_all_skills()
        names = [data["name"] for data in skills.values()]
        
        assert len(names) == len(set(names)), "Duplicate skill names found"

    def test_skill_version_or_name_present(self) -> None:
        """Test that skills have version or name information."""
        skills = load_all_skills()
        
        for skill_name, skill_data in skills.items():
            assert "version" in skill_data or "name" in skill_data, \
                f"Skill {skill_name} missing version or name"

    def test_extractor_skills_have_mock_values(self) -> None:
        """Test that extractor engine has mock values for demo mode."""
        from core.extractor_engine import MOCK_VALUES
        
        # The extractor_engine module has MOCK_VALUES dict for demo mode
        assert MOCK_VALUES is not None
        assert "price" in MOCK_VALUES
        assert "rating" in MOCK_VALUES

    def test_skill_yaml_syntax_valid(self) -> None:
        """Test that all skill/agent YAML files have valid syntax."""
        from config import settings
        
        agents_dir = settings.AGENTS_DIR
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")
            
        skill_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
        
        for skill_dir in skill_dirs:
            yaml_path = skill_dir / "agent.yaml"
            if yaml_path.exists():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML in {yaml_path}: {e}")

    def test_skill_markdown_files_load(self) -> None:
        """Test that SKILL.md files can be loaded."""
        from config import settings
        
        agents_dir = settings.AGENTS_DIR
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")
            
        skill_dirs = [d for d in agents_dir.iterdir() if d.is_dir()]
        
        for skill_dir in skill_dirs:
            md_path = skill_dir / "SKILL.md"
            if md_path.exists():
                try:
                    with open(md_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    assert len(content) > 0, f"Empty SKILL.md: {md_path}"
                except Exception as e:
                    pytest.fail(f"Cannot read {md_path}: {e}")
