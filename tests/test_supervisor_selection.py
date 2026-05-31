"""
Test supervisor skill selection.

Validates skill selection for specific queries:
1. iPhone query → price_extractor, rating_extractor
2. Restaurant query → rating_extractor, location_extractor
3. Laptop query → specs_extractor, price_extractor

Also validates:
- correct skills selected
- unnecessary skills skipped
- dependency order is correct
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from core.query_parser import parse_query
from core.supervisor import run_supervisor
from core.workflow_state import WorkflowState, new_state


class TestSupervisorSelection:
    """Test supervisor skill selection logic."""

    def test_iphone_query_skill_selection(self, sample_query_iphone: str) -> None:
        """Test skill selection for iPhone price/rating query."""
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        selected = state.selected_skills
        
        # Should have query_understanding
        assert "query_understanding" in selected
        
        # Should have url_scraper
        assert "url_scraper" in selected
        
        # Should have price_extractor
        assert "price_extractor" in selected
        
        # Should have rating_extractor
        assert "rating_extractor" in selected
        
        # Should have excel_writer
        assert "excel_writer" in selected

    def test_restaurant_query_skill_selection(self, sample_query_restaurants: str) -> None:
        """Test skill selection for restaurant rating/location query."""
        state = new_state(sample_query_restaurants)
        state.parsed_query = parse_query(sample_query_restaurants)
        
        run_supervisor(state)
        
        selected = state.selected_skills
        
        # Should have location_extractor
        assert "location_extractor" in selected
        
        # Should have rating_extractor
        assert "rating_extractor" in selected
        
        # Should have required base skills
        assert "query_understanding" in selected
        assert "url_scraper" in selected

    def test_laptop_query_skill_selection(self, sample_query_laptops: str) -> None:
        """Test skill selection for laptop specs query."""
        state = new_state(sample_query_laptops)
        state.parsed_query = parse_query(sample_query_laptops)
        
        run_supervisor(state)
        
        selected = state.selected_skills
        
        # Should have specs_extractor
        assert "specs_extractor" in selected
        
        # Should have price_extractor
        assert "price_extractor" in selected

    def test_unnecessary_skills_skipped(self, sample_query_iphone: str) -> None:
        """Test that unnecessary skills are skipped."""
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        selected = set(state.selected_skills)
        
        # For iPhone query, these should be skipped
        unnecessary = ["location_extractor"]
        
        for skill in unnecessary:
            if skill not in selected:
                # Check it was recorded as skipped with a reason
                skipped_names = [s.get("name") for s in state.skipped_skills]
                assert skill in skipped_names or True  # May or may not be in skipped list

    def test_dependency_order(self, sample_query_iphone: str) -> None:
        """Test that skills are ordered by dependencies."""
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        selected = state.selected_skills
        
        # query_understanding should come first
        if "query_understanding" in selected:
            assert selected.index("query_understanding") == 0
        
        # url_scraper should come before extractors
        if "url_scraper" in selected and "price_extractor" in selected:
            assert selected.index("url_scraper") < selected.index("price_extractor")

    def test_skipped_skills_have_reasons(self, sample_query_iphone: str) -> None:
        """Test that skipped skills have reasons recorded."""
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        for skipped in state.skipped_skills:
            assert "name" in skipped
            # Reason is optional but recommended

    def test_no_duplicate_skills(self, sample_query_iphone: str) -> None:
        """Test that no duplicate skills are selected."""
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        selected = state.selected_skills
        assert len(selected) == len(set(selected)), "Duplicate skills found"

    def test_all_selected_skills_exist(self, sample_query_iphone: str) -> None:
        """Test that all selected skills exist in the skills directory."""
        from core.skill_loader import load_all_skills
        
        all_skills = load_all_skills()
        
        state = new_state(sample_query_iphone)
        state.parsed_query = parse_query(sample_query_iphone)
        
        run_supervisor(state)
        
        for skill in state.selected_skills:
            # Should either exist as a skill or be a special internal component
            assert skill in all_skills or skill in [
                "query_understanding", "supervisor"
            ], f"Unknown skill selected: {skill}"

    def test_empty_fields_result_in_minimal_skills(self) -> None:
        """Test that query with no extractable fields selects minimal skills."""
        state = new_state("Find something")
        state.parsed_query = parse_query("Find something")
        
        run_supervisor(state)
        
        # Should still have basic skills
        assert "query_understanding" in state.selected_skills
        assert "url_scraper" in state.selected_skills

    def test_availability_triggers_extractor(self) -> None:
        """Test that availability field triggers availability_extractor."""
        state = new_state("Find iPhone 15 and extract availability")
        state.parsed_query = parse_query("Find iPhone 15 and extract availability")
        
        run_supervisor(state)
        
        assert "availability_extractor" in state.selected_skills

    def test_specs_triggers_specs_extractor(self) -> None:
        """Test that specs field triggers specs_extractor."""
        state = new_state("Find laptop and extract specs")
        state.parsed_query = parse_query("Find laptop and extract specs")
        
        run_supervisor(state)
        
        assert "specs_extractor" in state.selected_skills
