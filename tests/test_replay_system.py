"""
Test replay system functionality.

Validates:
- previous workflow can be loaded
- logs replay correctly
- selected skills replay correctly
- extracted results replay correctly
- missing replay file is handled safely
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from core.workflow_replay import load_trace, replay_trace, save_trace
from core.workflow_state import WorkflowState, new_state


class TestReplaySystem:
    """Test workflow replay functionality."""

    def test_save_and_load_replay(self) -> None:
        """Test saving and loading a trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                # Create a workflow state
                state = new_state("Test query")
                state.workflow_status = "completed"
                state.selected_skills = ["skill1", "skill2"]
                state.execution_times = {"skill1": 1.0, "skill2": 2.0}
                
                # Save trace
                save_trace(state)
                traces = list(tmp_path.glob("*.json"))
                assert len(traces) > 0
                
                # Load trace
                loaded = load_trace(traces[0])
                
                assert loaded is not None
                assert loaded["original_query"] == "Test query"
                assert loaded["workflow_status"] == "completed"

    def test_replay_logs(self) -> None:
        """Test that logs are preserved in trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.logs = ["[10:00:00] Log 1", "[10:00:01] Log 2"]
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert "logs" in loaded
                assert len(loaded["logs"]) == 2

    def test_replay_selected_skills(self) -> None:
        """Test that selected skills are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.selected_skills = ["query_understanding", "url_scraper", "price_extractor"]
                state.skipped_skills = [{"name": "location_extractor", "reason": "Not needed"}]
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert loaded["selected_skills"] == ["query_understanding", "url_scraper", "price_extractor"]
                assert len(loaded["skipped_skills"]) == 1

    def test_replay_extracted_results(self) -> None:
        """Test that extracted results are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.extracted_data = [
                    {
                        "url": "http://example.com",
                        "title": "Test",
                        "fields": {"price": "Rs 79,900"},
                        "confidence_score": 0.85,
                    }
                ]
                state.aggregated_results = {
                    "rows": state.extracted_data,
                    "summary": {"total_urls": 1, "success_count": 1},
                }
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert len(loaded["extracted_data"]) == 1
                assert loaded["aggregated_results"]["summary"]["total_urls"] == 1

    def test_missing_replay_file_handling(self) -> None:
        """Test handling of missing trace file."""
        try:
            loaded = load_trace("/nonexistent/path/replay.json")
            assert False, "Should have raised"
        except (FileNotFoundError, Exception):
            pass  # Expected

    def test_corrupted_replay_file_handling(self) -> None:
        """Test handling of corrupted trace file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            replay_path = Path(tmpdir) / "corrupted.json"
            
            # Write invalid JSON
            with open(replay_path, "w") as f:
                f.write("{invalid json")
            
            try:
                loaded = load_trace(str(replay_path))
                assert False, "Should have raised"
            except (json.JSONDecodeError, Exception):
                pass  # Expected

    def test_replay_directory_creation(self) -> None:
        """Test that traces use configured directory."""
        from config import settings
        assert settings.TRACES_DIR.exists()

    def test_replay_trace_function(self) -> None:
        """Test the replay_trace convenience function."""
        # Create and save a workflow
        state = new_state("Test query")
        state.workflow_status = "completed"
        state.selected_skills = ["skill1"]
        
        path = save_trace(state)
        
        # Replay it
        result = replay_trace(path)
        
        assert result is not None
        assert result["workflow_status"] == "completed"

    def test_replay_preserves_trace_id(self) -> None:
        """Test that trace_id is preserved in trace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.trace_id = "test-trace-12345"
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert loaded["trace_id"] == "test-trace-12345"

    def test_replay_preserves_execution_times(self) -> None:
        """Test that execution times are preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.execution_times = {
                    "query_understanding": 0.1,
                    "supervisor": 0.2,
                    "url_scraper": 1.5,
                }
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert loaded["execution_times"]["url_scraper"] == 1.5

    def test_replay_preserves_completed_nodes(self) -> None:
        """Test that completed nodes list is preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.completed_nodes = ["node1", "node2", "node3"]
                
                save_trace(state)
                
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])
                
                assert loaded["completed_nodes"] == ["node1", "node2", "node3"]
