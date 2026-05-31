"""
Test query parser functionality.

Validates:
- search_query extraction
- requested field extraction
- limit extraction
- fallback limit = 5
- malformed queries do not crash
"""

from __future__ import annotations

import pytest

from core.query_parser import FIELD_SYNONYMS, parse_query


class TestQueryParser:
    """Test query parsing functionality."""

    def test_basic_query_parsing(self) -> None:
        """Test basic query parsing with all components."""
        query = "Find top 5 URLs for iPhone 15 and extract price and rating"
        result = parse_query(query)
        
        assert result["search_query"] == "iPhone 15"
        assert "price" in result["requested_fields"]
        assert "rating" in result["requested_fields"]
        assert result["limit"] == 5

    def test_extract_price_only(self) -> None:
        """Test query with only price extraction."""
        query = "Find iPhone 15 and extract price"
        result = parse_query(query)
        
        assert "price" in result["requested_fields"]
        assert result["search_query"] == "iPhone 15"

    def test_extract_rating_only(self) -> None:
        """Test query with only rating extraction."""
        query = "Find iPhone 15 and extract rating"
        result = parse_query(query)
        
        assert "rating" in result["requested_fields"]

    def test_multiple_fields(self) -> None:
        """Test query with multiple field extractions."""
        query = "Find laptops and extract RAM, processor, storage, and price"
        result = parse_query(query)
        
        # Query parser groups RAM/processor/storage into "specs" field
        assert "specs" in result["requested_fields"] or "ram" in result["requested_fields"]
        assert "price" in result["requested_fields"]

    def test_restaurant_location_query(self) -> None:
        """Test restaurant query with location."""
        query = "Find restaurants in Bangalore and extract rating and location"
        result = parse_query(query)
        
        assert "rating" in result["requested_fields"]
        assert "location" in result["requested_fields"]
        assert "Bangalore" in result["search_query"] or "restaurants in Bangalore" in result["search_query"]

    def test_default_limit_is_5(self) -> None:
        """Test that default limit is 5 when not specified."""
        query = "Find iPhone 15 and extract price"
        result = parse_query(query)
        
        assert result["limit"] == 5

    def test_custom_limit_extraction(self) -> None:
        """Test custom limit extraction."""
        query = "Find top 10 URLs for iPhone 15 and extract price"
        result = parse_query(query)
        
        assert result["limit"] == 10

    def test_limit_bounds(self) -> None:
        """Test that limit respects min/max bounds."""
        # Too high
        result = parse_query("Find top 100 URLs for iPhone 15")
        assert result["limit"] <= 20  # Should be clamped to reasonable max
        
        # Too low
        result = parse_query("Find top 0 URLs for iPhone 15")
        assert result["limit"] >= 1  # Should be at least 1

    def test_field_synonyms_recognition(self) -> None:
        """Test that field synonyms are recognized."""
        # Test "cost" synonym for price
        result = parse_query("Find iPhone 15 and extract cost")
        assert "price" in result["requested_fields"] or "cost" in result["requested_fields"]
        
        # Test "reviews" synonym for rating
        result = parse_query("Find iPhone 15 and extract reviews")
        assert "rating" in result["requested_fields"] or "reviews" in result["requested_fields"]

    def test_empty_query_handling(self) -> None:
        """Test handling of empty queries."""
        result = parse_query("")
        
        # Should not crash and return valid structure
        assert "search_query" in result
        assert "requested_fields" in result
        assert isinstance(result["requested_fields"], list)

    def test_malformed_query_no_crash(self) -> None:
        """Test that malformed queries don't crash."""
        malformed_queries = [
            "just random text",
            "12345",
            "!@#$%",
            "extract ",
            "find and extract",
        ]
        
        for query in malformed_queries:
            result = parse_query(query)
            # Should return a dict with expected keys
            assert isinstance(result, dict)
            assert "search_query" in result
            assert "requested_fields" in result

    def test_availability_field_extraction(self) -> None:
        """Test extraction of availability field."""
        query = "Find iPhone 15 and extract availability"
        result = parse_query(query)
        
        assert "availability" in result["requested_fields"]

    def test_specs_field_extraction(self) -> None:
        """Test extraction of specs fields."""
        query = "Find laptops and extract specs"
        result = parse_query(query)
        
        # Should include common spec fields
        fields = result["requested_fields"]
        assert any(f in fields for f in ["specs", "ram", "processor", "storage"])

    def test_query_without_extract_verb(self) -> None:
        """Test query without explicit 'extract' verb."""
        query = "Find iPhone 15 price and rating"
        result = parse_query(query)
        
        # Should still extract fields; search_query may include the fields
        assert "iPhone 15" in result["search_query"]
        assert "price" in result["requested_fields"]

    def test_original_query_preserved(self) -> None:
        """Test that original query is preserved in result."""
        query = "Find top 5 URLs for iPhone 15 and extract price"
        result = parse_query(query)
        
        assert result.get("raw") == query or result.get("original_query") == query

    def test_entity_extraction(self) -> None:
        """Test entity extraction from queries."""
        test_cases = [
            ("Find iPhone 15", "iPhone 15"),
            ("Find Samsung Galaxy S24", "Samsung Galaxy S24"),
            ("Find restaurants in Delhi", "restaurants in Delhi"),
            ("Find gaming laptops", "gaming laptops"),
        ]
        
        for query, expected_entity in test_cases:
            result = parse_query(query)
            assert expected_entity in result["search_query"] or result["search_query"] in expected_entity
