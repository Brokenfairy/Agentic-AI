#!/usr/bin/env python3
"""
SkillFlow AI Final Readiness Check Script.

This script performs a comprehensive system health check and generates
a readiness score from 0-100 points.

Usage:
    python final_check.py

Scoring:
    - Environment check: 10 points
    - Skill loading: 10 points
    - Supervisor selection: 15 points
    - Workflow execution: 20 points
    - Extraction: 15 points
    - Excel export: 10 points
    - Langfuse mock: 10 points
    - Replay: 5 points
    - UI imports: 5 points
    Total: 100 points
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure test environment
os.environ["DEMO_MODE"] = "true"
os.environ["PYTEST_CURRENT_TEST"] = "1"


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_result(check_name: str, passed: bool, message: str = "") -> None:
    """Print a check result."""
    status = "PASS" if passed else "FAIL"
    msg = f" - {message}" if message else ""
    print(f"  {status}: {check_name}{msg}")


class ReadinessChecker:
    """System readiness checker with scoring."""

    def __init__(self) -> None:
        self.scores: Dict[str, Tuple[int, int]] = {}  # category: (earned, max)
        self.checks: List[Dict[str, Any]] = []

    def check(
        self,
        category: str,
        check_name: str,
        test_func,
        points: int,
        critical: bool = False,
    ) -> bool:
        """Run a single check and record the result."""
        try:
            result = test_func()
            passed = bool(result)
        except Exception as e:
            passed = False
            result = str(e)

        self.checks.append({
            "category": category,
            "name": check_name,
            "passed": passed,
            "points": points if passed else 0,
            "max_points": points,
            "result": result,
            "critical": critical,
        })

        if category not in self.scores:
            self.scores[category] = (0, 0)

        earned, max_p = self.scores[category]
        if passed:
            earned += points
        max_p += points
        self.scores[category] = (earned, max_p)

        print_result(check_name, passed, str(result) if not passed else "")
        return passed

    def total_score(self) -> Tuple[int, int]:
        """Calculate total score."""
        total_earned = sum(e for e, _ in self.scores.values())
        total_max = sum(m for _, m in self.scores.values())
        return total_earned, total_max

    def print_summary(self) -> None:
        """Print final summary report."""
        print_header("FINAL READINESS REPORT")

        print("\nCategory Scores:")
        print(f"  {'Category':<30} {'Score':>10} {'Max':>10}")
        print(f"  {'-' * 30} {'-' * 10} {'-' * 10}")

        for category, (earned, max_p) in sorted(self.scores.items()):
            print(f"  {category:<30} {earned:>10} {max_p:>10}")

        total_earned, total_max = self.total_score()
        percentage = (total_earned / total_max * 100) if total_max > 0 else 0

        print(f"\n  {'TOTAL':<30} {total_earned:>10} {total_max:>10}")
        print(f"\n  READINESS SCORE: {percentage:.1f}% ({total_earned}/{total_max})")

        # Status
        if percentage >= 90:
            print("\n  STATUS: EXCELLENT - System is demo-ready!")
        elif percentage >= 75:
            print("\n  STATUS: GOOD - System is functional with minor issues")
        elif percentage >= 50:
            print("\n  STATUS: FAIR - System needs attention before demo")
        else:
            print("\n  STATUS: POOR - System requires significant fixes")

        # Critical checks
        critical_failures = [c for c in self.checks if c["critical"] and not c["passed"]]
        if critical_failures:
            print("\n  ⚠️  CRITICAL FAILURES:")
            for check in critical_failures:
                print(f"    - {check['name']}: {check['result']}")

        return percentage >= 75  # Return True if passing threshold


def check_environment() -> bool:
    """Check environment configuration."""
    # Check .env.example exists
    env_example = Path(".env.example")
    if not env_example.exists():
        return False

    # Check requirements.txt exists
    requirements = Path("requirements.txt")
    if not requirements.exists():
        return False

    # Check Python version
    if sys.version_info < (3, 10):
        return False

    return True


def check_skill_loading() -> bool:
    """Check that skills load correctly."""
    try:
        from core.skill_loader import load_all_skills

        skills = load_all_skills()
        if not skills:
            return False

        # Check at least core skills exist
        required_skills = ["price_extractor", "rating_extractor", "url_scraper"]
        for skill in required_skills:
            if skill not in skills:
                return False

        return True
    except Exception as e:
        print(f"Skill loading error: {e}")
        return False


def check_supervisor_selection() -> bool:
    """Check supervisor skill selection."""
    try:
        from core.query_parser import parse_query
        from core.supervisor import run_supervisor
        from core.workflow_state import new_state

        # Test iPhone query
        state = new_state("Find top 5 URLs for iPhone 15 and extract price and rating")
        state.parsed_query = parse_query(state.original_query)
        run_supervisor(state)

        if "price_extractor" not in state.selected_skills:
            return False
        if "rating_extractor" not in state.selected_skills:
            return False

        return True
    except Exception as e:
        print(f"Supervisor error: {e}")
        return False


def check_workflow_execution() -> bool:
    """Check that workflow executes end-to-end."""
    try:
        from core.workflow_executor import run_workflow

        state = run_workflow(
            "Find top 3 URLs for iPhone 15 and extract price",
            on_event=lambda x: None,
        )

        return state.workflow_status == "completed"
    except Exception as e:
        print(f"Workflow error: {e}")
        return False


def check_extraction() -> bool:
    """Check field extraction."""
    try:
        from core.extractor_engine import _extract_price, extract_fields

        # Test price extraction
        html = "<div>Price: Rs 79,900</div>"
        price, confidence = _extract_price(html)

        # Test full extraction
        result = extract_fields(html, ["price"])

        return price is not None and "fields" in result and "confidence_score" in result
    except Exception as e:
        print(f"Extraction error: {e}")
        return False


def check_excel_export() -> bool:
    """Check Excel export functionality."""
    try:
        import tempfile
        from pathlib import Path

        from tools.excel_writer_tool import write_excel

        with tempfile.TemporaryDirectory() as tmpdir:
            rows = [
                {
                    "Query": "Test",
                    "Website": "test.com",
                    "URL": "http://test.com",
                    "Title": "Test",
                    "Price": "Rs 100",
                    "Rating": "4/5",
                    "Availability": "In Stock",
                    "Location": "",
                    "Specs": "",
                    "Confidence Score": 0.85,
                    "Fallback Used": "No",
                    "Status": "success",
                    "Method": "requests",
                    "Timestamp": "2024-01-01T00:00:00Z",
                }
            ]

            result = write_excel(rows, query="Test", output_dir=tmpdir)

            if result["rows_written"] != 1:
                return False

            if not Path(result["excel_path"]).exists():
                return False

            return True
    except Exception as e:
        print(f"Excel export error: {e}")
        return False


def check_langfuse_mock() -> bool:
    """Check Langfuse integration with mock."""
    try:
        from unittest.mock import MagicMock, patch

        from core.workflow_state import new_state
        from langfuse_config import LangfuseTracker

        mock_client = MagicMock()

        with patch("langfuse_config._CLIENT", mock_client):
            state = new_state("Test query")
            tracker = LangfuseTracker(state)

            span_id = tracker.start_span("test_skill")
            tracker.end_span(span_id)
            tracker.end()

            return True
    except Exception as e:
        print(f"Langfuse error: {e}")
        return False


def check_replay_system() -> bool:
    """Check replay system."""
    try:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from core.workflow_replay import load_trace, save_trace
        from core.workflow_state import new_state

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            with patch("core.workflow_replay.settings.TRACES_DIR", tmp_path):
                state = new_state("Test query")
                state.workflow_status = "completed"

                save_trace(state)
                traces = list(tmp_path.glob("*.json"))
                loaded = load_trace(traces[0])

                return loaded is not None and loaded["workflow_status"] == "completed"
    except Exception as e:
        print(f"Replay error: {e}")
        return False


def check_ui_imports() -> bool:
    """Check that UI components import successfully."""
    try:
        import app
        from components import (
            render_execution_timeline,
            render_observability_panel,
            render_skill_cards,
            render_workflow_graph,
        )

        # Check demo queries exist
        if not hasattr(app, "DEMO_QUERIES") or not app.DEMO_QUERIES:
            return False

        return True
    except Exception as e:
        print(f"UI import error: {e}")
        return False


def check_url_scraper() -> bool:
    """Check URL scraper with mock."""
    try:
        from tools.web_search_tool import search_web

        result = search_web("iPhone 15", limit=5, allow_mock=True)

        return "results" in result and len(result["results"]) > 0
    except Exception as e:
        print(f"URL scraper error: {e}")
        return False


def check_query_parser() -> bool:
    """Check query parser."""
    try:
        from core.query_parser import parse_query

        result = parse_query("Find iPhone 15 and extract price and rating")

        return (
            "search_query" in result
            and "requested_fields" in result
            and len(result["requested_fields"]) > 0
        )
    except Exception as e:
        print(f"Query parser error: {e}")
        return False


def check_page_reader() -> bool:
    """Check page reader."""
    try:
        from unittest.mock import MagicMock, patch

        from tools.page_reader import read_page

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = MagicMock(return_value=None)

        with patch("requests.get", return_value=mock_response):
            result = read_page("https://example.com")

            return result["status"] == "success"
    except Exception as e:
        print(f"Page reader error: {e}")
        return False


def check_folder_structure() -> bool:
    """Check that required folders exist."""
    required_folders = [
        "skills",
        "agents",
        "config",
        "core",
        "tools",
        "components",
        "tests",
        "outputs",
        "traces",
        "docs",
    ]

    for folder in required_folders:
        if not Path(folder).exists():
            return False

    return True


def main() -> int:
    """Main entry point."""
    print_header("SkillFlow AI Final Readiness Check")
    print(f"Working directory: {Path.cwd()}")
    print(f"Python version: {sys.version}")

    checker = ReadinessChecker()

    # 1. Environment Check (10 points)
    print_header("1. Environment Check (10 pts)")
    checker.check("Environment", "Python 3.10+", check_environment, 5, critical=True)
    checker.check("Environment", "Folder structure", check_folder_structure, 5)

    # 2. Skill Loading (10 points)
    print_header("2. Skill Loading (10 pts)")
    checker.check("Skill Loading", "YAML skills load", check_skill_loading, 10, critical=True)

    # 3. Supervisor Selection (15 points)
    print_header("3. Supervisor Selection (15 pts)")
    checker.check("Supervisor", "Skill selection logic", check_supervisor_selection, 10, critical=True)
    checker.check("Supervisor", "Query parser works", check_query_parser, 5)

    # 4. Workflow Execution (20 points)
    print_header("4. Workflow Execution (20 pts)")
    checker.check("Workflow", "End-to-end execution", check_workflow_execution, 15, critical=True)
    checker.check("Workflow", "URL scraper mock", check_url_scraper, 5)

    # 5. Extraction (15 points)
    print_header("5. Extraction (15 pts)")
    checker.check("Extraction", "Field extraction", check_extraction, 10, critical=True)
    checker.check("Extraction", "Page reader mock", check_page_reader, 5)

    # 6. Excel Export (10 points)
    print_header("6. Excel Export (10 pts)")
    checker.check("Excel Export", "File generation", check_excel_export, 10, critical=True)

    # 7. Langfuse Mock (10 points)
    print_header("7. Langfuse Integration (10 pts)")
    checker.check("Langfuse", "Mock client works", check_langfuse_mock, 10)

    # 8. Replay (5 points)
    print_header("8. Replay System (5 pts)")
    checker.check("Replay", "Save/load replay", check_replay_system, 5)

    # 9. UI Imports (5 points)
    print_header("9. UI Components (5 pts)")
    checker.check("UI", "Component imports", check_ui_imports, 5)

    # Print summary
    passing = checker.print_summary()

    # Save detailed report
    report_path = Path("final_readiness_report.txt")
    with open(report_path, "w") as f:
        f.write("SkillFlow AI Final Readiness Report\n")
        f.write("=" * 60 + "\n\n")

        for check in checker.checks:
            status = "PASS" if check["passed"] else "FAIL"
            f.write(f"[{status}] {check['category']} - {check['name']}\n")
            if not check["passed"] and check["result"]:
                f.write(f"      Error: {check['result']}\n")

        total_earned, total_max = checker.total_score()
        percentage = (total_earned / total_max * 100) if total_max > 0 else 0
        f.write(f"\nFinal Score: {total_earned}/{total_max} ({percentage:.1f}%)\n")

    print(f"\nDetailed report saved to: {report_path}")

    return 0 if passing else 1


if __name__ == "__main__":
    sys.exit(main())
