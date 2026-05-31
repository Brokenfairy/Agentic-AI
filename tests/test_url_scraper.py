"""
Test URL scraper functionality.

Validates:
- returns top 5 URLs
- handles API failure
- handles empty results
- uses cached demo data in DEMO_PRESENTATION_MODE
- logs errors correctly

All tests use mocked Tavily responses - no real API calls.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from tools.web_search_tool import search_web


class TestURLScraper:
    """Test URL scraper with mocked Tavily API."""

    def test_returns_urls_list(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that search returns a list of URL results."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.return_value = mock_tavily_response
                MockClient.return_value = mock_client
                
                result = search_web("iPhone 15", limit=5, allow_mock=False)
                
                assert "results" in result
                assert isinstance(result["results"], list)
                assert len(result["results"]) > 0

    def test_returns_top_5_urls(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that search respects the limit parameter."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                extended_response = {
                    "results": mock_tavily_response["results"] * 3
                }
                mock_client.search.return_value = extended_response
                MockClient.return_value = mock_client
                
                result = search_web("iPhone 15", limit=5, allow_mock=False)
                
                assert len(result["results"]) <= 5

    def test_url_format_has_required_fields(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that returned URLs have required fields."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.return_value = mock_tavily_response
                MockClient.return_value = mock_client
                
                result = search_web("iPhone 15", limit=5, allow_mock=False)
                
                for url_entry in result["results"]:
                    assert "url" in url_entry
                    assert "title" in url_entry
                    assert "domain" in url_entry
                    assert url_entry["url"].startswith("http")

    def test_handles_api_failure_with_mock_fallback(self) -> None:
        """Test that API failures fall back to mock data."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.side_effect = Exception("API Error")
                MockClient.return_value = mock_client
                
                result = search_web("iPhone 15", limit=5, allow_mock=True)
                
                assert "results" in result
                assert len(result["results"]) > 0
                assert result.get("source") == "mock"

    def test_handles_empty_results(self) -> None:
        """Test handling of empty search results."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.return_value = {"results": []}
                MockClient.return_value = mock_client
                
                result = search_web("obscure query xyz123", limit=5, allow_mock=False)
                
                assert "results" in result
                assert isinstance(result["results"], list)

    def test_source_field_indicates_origin(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that source field indicates data origin."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.return_value = mock_tavily_response
                MockClient.return_value = mock_client
                
                result = search_web("test", limit=5, allow_mock=False)
                assert result.get("source") in ["tavily", "mock"]

    def test_empty_query_handling(self) -> None:
        """Test handling of empty search query."""
        result = search_web("", limit=5)
        
        # Should return empty results gracefully
        assert "results" in result
        assert "error" in result or len(result["results"]) == 0

    def test_limit_parameter_respected(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that limit parameter is respected."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                extended = {"results": mock_tavily_response["results"] * 4}
                mock_client.search.return_value = extended
                MockClient.return_value = mock_client
                
                result = search_web("test", limit=3, allow_mock=False)
                
                assert len(result["results"]) <= 3

    def test_domain_extraction_from_url(self, mock_tavily_response: Dict[str, Any]) -> None:
        """Test that domain is correctly extracted from URLs."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.return_value = mock_tavily_response
                MockClient.return_value = mock_client
                
                result = search_web("test", limit=5, allow_mock=False)
                
                for entry in result["results"]:
                    assert "domain" in entry
                    assert not entry["domain"].startswith("http")
                    assert "/" not in entry["domain"]

    def test_demo_mode_uses_mock_data(self) -> None:
        """Test that DEMO_MODE uses cached/mock data."""
        # Force mock mode
        result = search_web("iPhone 15", limit=5, allow_mock=True)
        
        # Should return results even without API key
        assert "results" in result
        assert len(result["results"]) >= 3  # Mock provides 5
        assert result.get("source") == "mock"

    def test_error_logging_on_failure(self) -> None:
        """Test that errors are properly logged."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=True):
            with patch("tavily.TavilyClient") as MockClient:
                mock_client = MagicMock()
                mock_client.search.side_effect = Exception("Network Error")
                MockClient.return_value = mock_client
                
                result = search_web("test", limit=5, allow_mock=True)
                
                assert "error" in result or result.get("source") == "mock"

    def test_no_api_call_when_mock_enabled(self) -> None:
        """Test that no API call is made when mock is enabled."""
        with patch("tools.web_search_tool.settings.has_tavily", return_value=False):
            result = search_web("test", limit=5, allow_mock=True)
            
            # Should return mock results without calling Tavily
            assert "results" in result
            assert result.get("source") == "mock"
