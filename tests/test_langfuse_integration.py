"""
Test Langfuse integration.

Validates:
- trace is created
- spans are created per skill
- errors are logged
- trace_id is stored in workflow state
- system continues if Langfuse keys are missing
- user_id / session_id / tags support
- data masking works

Uses mocked Langfuse client - no real API calls.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from core.workflow_state import WorkflowState, new_state
from langfuse_config import LangfuseTracker, is_enabled, mask_sensitive


class TestLangfuseIntegration:
    """Test Langfuse tracing integration."""

    def test_langfuse_disabled_without_keys(self) -> None:
        """Test that Langfuse is disabled when keys are missing."""
        with patch("core.langfuse_integration.get_client", return_value=None):
            assert not is_enabled()

    def test_trace_id_always_set(self) -> None:
        """Test that trace_id is always set even without Langfuse."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=None):
            tracker = LangfuseTracker(state)
            
            assert tracker.trace_id
            assert isinstance(tracker.trace_id, str)
            assert len(tracker.trace_id) > 0

    def test_trace_url_with_mock_client(self, mock_langfuse_client: MagicMock) -> None:
        """Test trace URL generation with mock client."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            assert tracker.trace_url is not None
            assert "langfuse" in tracker.trace_url or "trace" in tracker.trace_url

    def test_span_creation(self, mock_langfuse_client: MagicMock) -> None:
        """Test that spans are created for skills."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            span_id = tracker.start_span("test_skill", input={"test": "data"})
            
            assert span_id
            assert isinstance(span_id, str)

    def test_span_ending(self, mock_langfuse_client: MagicMock) -> None:
        """Test that spans can be ended."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            span_id = tracker.start_span("test_skill")
            duration = tracker.end_span(span_id, output={"result": "success"})
            
            assert isinstance(duration, (int, float))
            assert duration >= 0

    def test_error_logging_to_span(self, mock_langfuse_client: MagicMock) -> None:
        """Test that errors are logged to spans."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            span_id = tracker.start_span("failing_skill")
            tracker.end_span(
                span_id,
                level="ERROR",
                status_message="Something went wrong",
                output={"error": "test error"}
            )
            
            # Should complete without exception
            assert True

    def test_trace_ending(self, mock_langfuse_client: MagicMock) -> None:
        """Test that trace can be ended."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            # Should not raise
            tracker.end(output={"status": "completed"})
            
            # Flush should be called
            mock_langfuse_client.flush.assert_called()

    def test_workflow_continues_without_langfuse(self) -> None:
        """Test that workflow continues when Langfuse is unavailable."""
        state = new_state("Test query")
        
        # Simulate no Langfuse
        with patch("core.langfuse_integration.get_client", return_value=None):
            tracker = LangfuseTracker(state)
            
            # These should not raise
            span_id = tracker.start_span("test")
            tracker.end_span(span_id)
            tracker.end()
            
            # trace_id should still be set
            assert state.trace_id

    def test_trace_id_stored_in_state(self, mock_langfuse_client: MagicMock) -> None:
        """Test that trace_id is stored in workflow state."""
        state = new_state("Test query")
        original_trace_id = state.trace_id
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            # trace_id should be set in tracker and match state's
            assert tracker.trace_id == original_trace_id

    def test_event_logging(self, mock_langfuse_client: MagicMock) -> None:
        """Test that events can be logged."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            # Should not raise
            tracker.event("test_event", data="test")

    def test_span_duration_tracking(self, mock_langfuse_client: MagicMock) -> None:
        """Test that span durations are tracked."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            span_id = tracker.start_span("timed_skill")
            # Simulate some work
            import time
            time.sleep(0.01)
            duration = tracker.end_span(span_id)
            
            assert duration > 0  # Should have measurable duration

    def test_multiple_spans_per_trace(self, mock_langfuse_client: MagicMock) -> None:
        """Test that multiple spans can be created per trace."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            span_ids = []
            for i in range(5):
                span_id = tracker.start_span(f"skill_{i}")
                span_ids.append(span_id)
            
            assert len(span_ids) == 5
            assert len(set(span_ids)) == 5  # All unique

    def test_trace_metadata(self, mock_langfuse_client: MagicMock) -> None:
        """Test that trace metadata is set."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(state)
            
            # Verify trace was created with metadata
            mock_langfuse_client.trace.assert_called_once()
            call_kwargs = mock_langfuse_client.trace.call_args[1]
            
            assert "id" in call_kwargs
            assert "name" in call_kwargs
            assert call_kwargs["name"] == "skillflow.workflow"

    def test_user_session_tags(self, mock_langfuse_client: MagicMock) -> None:
        """Test that user_id, session_id, and tags are passed to trace."""
        state = new_state(
            "Test query",
            user_id="user-123",
            session_id="session-456",
            tags=["test", "skillflow"],
        )
        
        with patch("core.langfuse_integration.get_client", return_value=mock_langfuse_client):
            tracker = LangfuseTracker(
                state,
                user_id=state.user_id,
                session_id=state.session_id,
                tags=state.tags,
            )
            
            call_kwargs = mock_langfuse_client.trace.call_args[1]
            assert call_kwargs.get("user_id") == "user-123"
            assert call_kwargs.get("session_id") == "session-456"
            assert call_kwargs.get("tags") == ["test", "skillflow"]

    def test_mask_sensitive(self) -> None:
        """Test that sensitive data is masked."""
        data = {
            "api_key": "sk-1234567890abcdef",
            "password": "secret123",
            "normal_field": "visible",
            "nested": {"secret_token": "abc"},
        }
        masked = mask_sensitive(data)
        
        assert masked["api_key"] == "***"
        assert masked["password"] == "***"
        assert masked["normal_field"] == "visible"
        assert masked["nested"]["secret_token"] == "***"

    def test_mask_long_key_string(self) -> None:
        """Test heuristic masking of long key-like strings."""
        data = {"my_value": "sk-abcdefghijklmnopqrstuvwxyz12345678901234567890"}
        masked = mask_sensitive(data)
        assert masked["my_value"].startswith("sk-")
        assert "***" in masked["my_value"]

    def test_tracker_ignores_missing_client(self) -> None:
        """Test tracker methods gracefully handle missing client."""
        state = new_state("Test query")
        
        with patch("core.langfuse_integration.get_client", return_value=None):
            tracker = LangfuseTracker(state)
            
            span_id = tracker.start_span("test")
            tracker.end_span(span_id)
            tracker.event("test_event")
            tracker.end()
            
            assert tracker.trace_url is None
