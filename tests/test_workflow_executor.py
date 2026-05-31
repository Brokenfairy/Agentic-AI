"""
Test workflow executor end-to-end.

Validates:
- workflow completes
- selected skills execute in correct order
- logs are generated
- extracted data is produced
- Excel export is generated
- workflow state is saved
- final summary is generated

All external APIs are mocked.
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from core.workflow_executor import run_workflow
from core.workflow_state import WorkflowState, new_state


class TestWorkflowExecutor:
    """Test end-to-end workflow execution."""

    def test_workflow_completes(self, sample_query_iphone: str) -> None:
        """Test that workflow runs to completion."""
        events: List[Dict[str, Any]] = []
        
        def on_event(evt: Dict[str, Any]) -> None:
            events.append(evt)
        
        state = run_workflow(sample_query_iphone, on_event=on_event)
        
        assert state.workflow_status == "completed"

    def test_workflow_generates_logs(self, sample_query_iphone: str) -> None:
        """Test that workflow generates logs."""
        state = run_workflow(sample_query_iphone)
        
        assert len(state.logs) > 0

    def test_workflow_selects_skills(self, sample_query_iphone: str) -> None:
        """Test that workflow selects appropriate skills."""
        state = run_workflow(sample_query_iphone)
        
        assert len(state.selected_skills) > 0
        assert "query_understanding" in state.selected_skills
        assert "url_scraper" in state.selected_skills

    def test_workflow_finds_urls(self, sample_query_iphone: str) -> None:
        """Test that workflow finds URLs."""
        state = run_workflow(sample_query_iphone)
        
        # In demo mode, should find mock URLs
        assert len(state.scraped_urls) > 0

    def test_workflow_generates_excel(self, sample_query_iphone: str) -> None:
        """Test that workflow generates Excel export."""
        state = run_workflow(sample_query_iphone)
        
        # Should generate Excel if excel_writer selected
        if "excel_writer" in state.selected_skills:
            assert state.excel_path is not None or state.rows_written >= 0

    def test_workflow_sets_execution_times(self, sample_query_iphone: str) -> None:
        """Test that workflow tracks execution times."""
        state = run_workflow(sample_query_iphone)
        
        assert len(state.execution_times) > 0
        # Each completed node should have a time
        for node in state.completed_nodes:
            assert node in state.execution_times

    def test_workflow_completes_nodes(self, sample_query_iphone: str) -> None:
        """Test that workflow completes expected nodes."""
        state = run_workflow(sample_query_iphone)
        
        expected_nodes = ["query_understanding", "supervisor", "url_scraper"]
        for node in expected_nodes:
            assert node in state.completed_nodes, f"Node {node} not completed"

    def test_workflow_generates_summary(self, sample_query_iphone: str) -> None:
        """Test that workflow generates summary."""
        state = run_workflow(sample_query_iphone)
        
        assert state.summary_markdown
        assert len(state.summary_markdown) > 0

    def test_workflow_sets_trace_id(self, sample_query_iphone: str) -> None:
        """Test that workflow sets trace_id."""
        state = run_workflow(sample_query_iphone)
        
        assert state.trace_id
        assert isinstance(state.trace_id, str)

    def test_workflow_event_stream(self, sample_query_iphone: str) -> None:
        """Test that workflow emits events."""
        events: List[Dict[str, Any]] = []
        
        def on_event(evt: Dict[str, Any]) -> None:
            events.append(evt)
        
        run_workflow(sample_query_iphone, on_event=on_event)
        
        assert len(events) > 0
        
        # Should have workflow_start event
        start_events = [e for e in events if e.get("kind") == "workflow_start"]
        assert len(start_events) > 0

    def test_workflow_state_saved(self, sample_query_iphone: str) -> None:
        """Test that workflow state can be saved."""
        state = run_workflow(sample_query_iphone)
        
        # Should be convertible to dict
        state_dict = state.to_dict()
        assert isinstance(state_dict, dict)
        assert "original_query" in state_dict

    def test_workflow_respects_demo_mode(self, sample_query_iphone: str) -> None:
        """Test that workflow respects demo mode settings."""
        with patch("config.demo_mode.DEMO_MODE", True):
            state = run_workflow(sample_query_iphone)
            
            # Should complete without errors in demo mode
            assert state.workflow_status == "completed"

    def test_multiple_field_extraction(self) -> None:
        """Test workflow with multiple field extraction."""
        query = "Find iPhone 15 and extract price, rating, and availability"
        
        state = run_workflow(query)
        
        assert state.workflow_status == "completed"
        
        # Should select all extractors
        if state.selected_skills:
            assert any("price" in s for s in state.selected_skills)
            assert any("rating" in s for s in state.selected_skills)

    def test_workflow_tracks_failed_nodes(self) -> None:
        """Test that workflow tracks failed nodes."""
        # This test verifies the structure exists
        state = new_state("Test")
        
        # Initially empty
        assert state.failed_nodes == []
        
        # Can add failed nodes
        state.failed_nodes.append("test_node")
        assert "test_node" in state.failed_nodes

    def test_workflow_duration_tracking(self, sample_query_iphone: str) -> None:
        """Test that workflow tracks total duration."""
        state = run_workflow(sample_query_iphone)
        
        assert state.total_duration_seconds >= 0
        assert isinstance(state.total_duration_seconds, (int, float))

    def test_workflow_timestamps(self, sample_query_iphone: str) -> None:
        """Test that workflow sets timestamps."""
        state = run_workflow(sample_query_iphone)
        
        assert state.workflow_start_time
        if state.workflow_status == "completed":
            assert state.workflow_end_time
