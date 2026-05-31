"""
Pytest fixtures for SkillFlow AI test suite.

All external API calls are mocked to ensure tests run without API keys.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# Ensure test environment
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("PYTEST_CURRENT_TEST", "1")


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Set up mock environment variables for testing."""
    env_backup = dict(os.environ)
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEMO_ALLOW_MOCK_SEARCH"] = "true"
    os.environ["DEMO_ALLOW_MOCK_EXTRACTION"] = "true"
    os.environ["DEMO_NEVER_FAIL_WORKFLOW"] = "true"
    yield
    os.environ.clear()
    os.environ.update(env_backup)


@pytest.fixture
def temp_outputs_dir() -> Generator[Path, None, None]:
    """Create a temporary outputs directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outputs_path = Path(tmpdir) / "outputs"
        outputs_path.mkdir(exist_ok=True)
        yield outputs_path


@pytest.fixture
def sample_query_iphone() -> str:
    """Sample query for iPhone price/rating extraction."""
    return "Find top 5 URLs for iPhone 15 and extract price and rating"


@pytest.fixture
def sample_query_restaurants() -> str:
    """Sample query for restaurant rating/location extraction."""
    return "Find restaurants in Bangalore and extract rating and location"


@pytest.fixture
def sample_query_laptops() -> str:
    """Sample query for laptop specs extraction."""
    return "Find laptops and extract RAM, processor, storage, and price"


@pytest.fixture
def mock_tavily_response() -> Dict[str, Any]:
    """Mock Tavily API response."""
    return {
        "results": [
            {
                "title": "iPhone 15 - Amazon.in",
                "url": "https://amazon.in/iphone-15",
                "content": "iPhone 15 price Rs 79900 rating 4.5 stars",
                "score": 0.95,
            },
            {
                "title": "iPhone 15 - Flipkart",
                "url": "https://flipkart.com/iphone-15",
                "content": "iPhone 15 price Rs 78999 rating 4.3 stars",
                "score": 0.92,
            },
            {
                "title": "iPhone 15 - Croma",
                "url": "https://croma.com/iphone-15",
                "content": "iPhone 15 price Rs 79900 rating 4.4 stars",
                "score": 0.88,
            },
        ]
    }


@pytest.fixture
def mock_web_search_results() -> List[Dict[str, str]]:
    """Mock web search results."""
    return [
        {"title": "iPhone 15 - Amazon", "url": "https://amazon.in/iphone-15", "domain": "amazon.in"},
        {"title": "iPhone 15 - Flipkart", "url": "https://flipkart.com/iphone-15", "domain": "flipkart.com"},
        {"title": "iPhone 15 - Croma", "url": "https://croma.com/iphone-15", "domain": "croma.com"},
    ]


@pytest.fixture
def mock_html_content() -> str:
    """Sample HTML content for page reader tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>iPhone 15 Product Page</title></head>
    <body>
        <h1>iPhone 15</h1>
        <div class="price">Rs 79,900</div>
        <div class="rating">4.5 out of 5 stars</div>
        <div class="availability">In Stock</div>
        <script>alert('test');</script>
        <style>.hidden { display: none; }</style>
    </body>
    </html>
    """


@pytest.fixture
def mock_extraction_result() -> Dict[str, Any]:
    """Mock extraction result."""
    return {
        "fields": {
            "price": "Rs 79,900",
            "rating": "4.5/5",
            "availability": "In Stock",
        },
        "confidence_score": 0.85,
        "fallback_used": False,
    }


@pytest.fixture
def mock_langfuse_client() -> MagicMock:
    """Mock Langfuse client."""
    mock_client = MagicMock()
    mock_trace = MagicMock()
    mock_span = MagicMock()
    
    mock_client.trace.return_value = mock_trace
    mock_trace.span.return_value = mock_span
    mock_trace.get_trace_url.return_value = "https://cloud.langfuse.com/trace/test-trace-id"
    
    return mock_client


@pytest.fixture
def mock_gemini_response() -> MagicMock:
    """Mock Gemini LLM response."""
    mock_response = MagicMock()
    mock_response.content = """
    {
        "price": "Rs 79,900",
        "rating": "4.5/5",
        "availability": "In Stock"
    }
    """
    return mock_response


@pytest.fixture
def mock_workflow_state() -> Dict[str, Any]:
    """Mock workflow state for testing."""
    return {
        "original_query": "Find iPhone 15 price",
        "parsed_query": {
            "search_query": "iPhone 15",
            "requested_fields": ["price", "rating"],
            "limit": 5,
        },
        "selected_skills": [
            "query_understanding",
            "url_scraper",
            "price_extractor",
            "rating_extractor",
            "excel_writer",
        ],
        "skipped_skills": [],
        "scraped_urls": [
            {"title": "iPhone 15 - Amazon", "url": "https://amazon.in/iphone-15", "domain": "amazon.in"},
        ],
        "extracted_data": [],
        "workflow_status": "completed",
        "completed_nodes": ["query_understanding", "supervisor", "url_scraper"],
        "failed_nodes": [],
        "execution_times": {"query_understanding": 0.1, "supervisor": 0.2},
        "trace_id": "test-trace-123",
    }


@pytest.fixture
def sample_skill_yaml() -> str:
    """Sample skill YAML content."""
    return """
name: price_extractor
version: "1.0"
description: Extracts product pricing information from webpages

inputs:
  - name: html_content
    type: string
    description: Raw HTML content from webpage
    required: true
  - name: url
    type: string
    description: Source URL for context
    required: false

outputs:
  - name: price
    type: string
    description: Extracted price in original format
  - name: currency
    type: string
    description: Detected currency code

triggers:
  - price
  - cost
  - amount
  - rs
  - ₹

dependencies:
  - url_scraper
"""


@pytest.fixture
def sample_skill_markdown() -> str:
    """Sample SKILL.md content."""
    return """# Price Extractor Skill

## Purpose
Extracts product pricing information from e-commerce webpages.

## Algorithm
1. Search for currency patterns (Rs, ₹, $, etc.)
2. Extract numeric values near currency symbols
3. Validate against reasonable price ranges
4. Return structured price data

## Limitations
- May not detect prices in images
- Currency detection depends on explicit symbols
- Dynamic prices (via JavaScript) require Playwright
"""


@pytest.fixture(autouse=True)
def reset_demo_mode() -> Generator[None, None, None]:
    """Reset demo mode settings before each test."""
    # Pre-test setup
    original_demo = os.environ.get("DEMO_MODE")
    os.environ["DEMO_MODE"] = "true"
    
    yield
    
    # Post-test cleanup
    if original_demo is not None:
        os.environ["DEMO_MODE"] = original_demo


@pytest.fixture
def mock_requests_response() -> MagicMock:
    """Mock requests.Response object."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
    <head><title>Test Product</title></head>
    <body>
        <div class="price">Rs 79,900</div>
        <div class="rating">4.5 stars</div>
    </body>
    </html>
    """
    mock_resp.raise_for_status = Mock(return_value=None)
    return mock_resp
