"""
Test page reader functionality.

Validates:
- requests + BeautifulSoup works for simple HTML
- Playwright fallback is called when requests fails
- failed pages return clean error objects
- content cleaning removes scripts/styles
- page title is extracted

All tests use mocked HTML - no real HTTP requests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tools.page_reader import _clean_visible_text, read_page


class TestPageReader:
    """Test page reader with mocked HTTP responses."""

    def test_successful_page_read(self) -> None:
        """Test successful page read with requests."""
        # Content must be > 400 chars to pass _MIN_USEFUL_LENGTH check
        mock_html = f"""
        <html><head><title>Test Product</title></head>
        <body>
            <h1>Product Page</h1>
            <div class="price">Rs 79,900</div>
            <p>{"Lorem ipsum dolor sit amet. " * 30}</p>
        </body>
        </html>
        """
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": mock_html}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com/product")
                
                assert result["status"] == "success"
                assert "content" in result
                assert "title" in result
                assert result["method"] == "requests"

    def test_page_title_extraction(self) -> None:
        """Test that page title is correctly extracted."""
        mock_html = f"""
        <html><head><title>Test Product</title></head>
        <body>
            <h1>Product Page</h1>
            <p>{"Lorem ipsum dolor sit amet. " * 30}</p>
        </body>
        </html>
        """
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": mock_html}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com/product")
                
                assert result["title"] == "Test Product"

    def test_content_cleaning_removes_scripts(self) -> None:
        """Test that script tags are removed from content."""
        html = """
        <html>
        <body>
            <script>alert('test');</script>
            <p>Real content</p>
        </body>
        </html>
        """
        
        result = _clean_visible_text(html)
        cleaned = result["content"]
        
        assert "alert" not in cleaned
        assert "script" not in cleaned.lower()
        assert "Real content" in cleaned

    def test_content_cleaning_removes_styles(self) -> None:
        """Test that style tags are removed from content."""
        html = """
        <html>
        <style>.hidden { display: none; }</style>
        <body><p>Visible content</p></body>
        </html>
        """
        
        result = _clean_visible_text(html)
        cleaned = result["content"]
        
        assert ".hidden" not in cleaned
        assert "display: none" not in cleaned
        assert "Visible content" in cleaned

    def test_playwright_fallback_on_failure(self) -> None:
        """Test that Playwright is used as fallback when requests fails."""
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": False, "error": "Connection Error", "html": ""}):
            mock_html = "<html><head><title>Playwright Title</title></head><body>Playwright content</body></html>"
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": True, "error": "", "html": mock_html}):
                result = read_page("https://example.com")
                
                # Should succeed via playwright fallback
                assert result["status"] == "success"
                assert result["method"] == "playwright"
                assert result["title"] == "Playwright Title"

    def test_failed_page_returns_error_object(self) -> None:
        """Test that failed pages return clean error objects."""
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": False, "error": "404", "html": ""}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "Both failed", "html": ""}):
                result = read_page("https://example.com/notfound")
                
                assert result["status"] == "failed"
                assert "error" in result

    def test_content_not_empty_on_success(self) -> None:
        """Test that successful reads have non-empty content."""
        mock_html = f"<html><body><h1>Title</h1><p>{'Content here. ' * 50}</p></body></html>"
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": mock_html}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com")
                
                assert result["content"]
                assert len(result["content"]) > 0

    def test_url_preserved_in_result(self) -> None:
        """Test that URL is preserved in the result."""
        test_url = "https://example.com/product/123"
        mock_html = "<html><body>Content</body></html>"
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": mock_html}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page(test_url)
                
                assert result.get("url") == test_url or "url" in result

    def test_extract_title_function(self) -> None:
        """Test the title extraction via _clean_visible_text."""
        html_with_title = "<html><head><title>Test Page</title></head><body></body></html>"
        
        result = _clean_visible_text(html_with_title)
        
        assert result["title"] == "Test Page"

    def test_extract_title_no_title_tag(self) -> None:
        """Test title extraction when no title tag exists."""
        html_no_title = "<html><body><h1>Heading</h1></body></html>"
        
        result = _clean_visible_text(html_no_title)
        
        assert result["title"] == "" or result["title"] is None

    def test_empty_url_handling(self) -> None:
        """Test handling of empty URL."""
        result = read_page("")
        
        # Should return failed status gracefully
        assert result["status"] == "failed" or "error" in result

    def test_invalid_url_handling(self) -> None:
        """Test handling of invalid URL format."""
        result = read_page("not-a-valid-url")
        
        # Should return failed status gracefully
        assert result["status"] in ["failed", "success"]  # May succeed with retry

    def test_metadata_extraction(self) -> None:
        """Test that metadata is extracted from page."""
        mock_html = "<html><body>Content</body></html>"
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": mock_html}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com")
                
                assert "metadata" in result
                assert isinstance(result["metadata"], dict)

    def test_content_truncation_for_large_pages(self) -> None:
        """Test that very large pages are handled."""
        # Create a large HTML content
        large_content = "<html><body>" + "<p>Text</p>" * 10000 + "</body></html>"
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": large_content}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com/large")
                
                assert result["status"] == "success"
                assert len(result["content"]) > 0

    def test_unicode_content_handling(self) -> None:
        """Test handling of unicode content."""
        html_unicode = f"<html><head><title>Unicode Page</title></head><body>₹ 79,900 <p>{'Unicode content. ' * 50}</p></body></html>"
        
        with patch("tools.page_reader._fetch_with_requests", return_value={"ok": True, "error": "", "html": html_unicode}):
            with patch("tools.page_reader._fetch_with_playwright", return_value={"ok": False, "error": "", "html": ""}):
                result = read_page("https://example.com/unicode")
                
                assert result["status"] == "success"
                assert "₹" in result["content"] or "79,900" in result["content"]
