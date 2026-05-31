"""Comprehensive evaluation harness for SkillFlow AI."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from core.workflow_executor import run_workflow
from core.recovery_engine import count_retries
from evals.metrics import extraction_metrics
from evals.reliability import reliability_metrics
from evals.scoring import selection_metrics


def _load_eval_config() -> dict:
    path = settings.BASE_DIR / "config" / "eval_config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_reports(payload: dict) -> dict:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    report_dir = settings.EVALS_DIR / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"evaluation_report_{ts}.json"
    md_path = report_dir / f"evaluation_report_{ts}.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    summary = payload.get("summary", {})
    lines = [
        "# Evaluation Report",
        "",
        f"- Cases: {summary.get('cases', 0)}",
        f"- Passed: {summary.get('passed_cases', 0)}",
        f"- Skill Precision: {summary.get('avg_skill_precision', 0.0)}",
        f"- Skill Recall: {summary.get('avg_skill_recall', 0.0)}",
        f"- Extraction Success Rate: {summary.get('avg_extraction_success_rate', 0.0)}",
        f"- Reliability Score: {summary.get('avg_reliability_score', 0.0)}",
        "",
        "## Failed Cases",
        "",
    ]
    for item in payload.get("failures", []):
        lines.append(f"- {item.get('query')}: {item.get('reasons')}")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _effective_thresholds(eval_config: dict) -> dict:
    if settings.has_google():
        return dict(eval_config)
    effective = dict(eval_config)
    effective["min_extraction_confidence"] = float(
        eval_config.get("fallback_min_extraction_confidence", eval_config.get("min_extraction_confidence", 0.0))
    )
    effective["min_skill_precision"] = float(
        eval_config.get("fallback_min_skill_precision", eval_config.get("min_skill_precision", 0.0))
    )
    effective["min_skill_recall"] = float(
        eval_config.get("fallback_min_skill_recall", eval_config.get("min_skill_recall", 0.0))
    )
    effective["mode"] = "heuristic_fallback"
    return effective


def main() -> int:
    cases = json.loads((settings.EVALS_DIR / "golden_cases.json").read_text(encoding="utf-8"))
    eval_config = _load_eval_config()
    thresholds = _effective_thresholds(eval_config)
    failures = []
    case_reports = []

    for case in cases:
        state = run_workflow(case["query"], enable_compare=False)
        rows = (state.aggregated_results or {}).get("rows") or []
        selection = selection_metrics(case.get("expected_skills") or [], state.selected_skills or [])
        extraction = extraction_metrics(rows, case.get("expected_fields") or [])
        reliability = reliability_metrics(state)

        passed = True
        reasons = []
        if case.get("workflow_should_complete", True) and state.workflow_status != "completed":
            passed = False
            reasons.append("workflow did not complete")
        if len(rows) < int(case.get("expected_min_results", 0)):
            passed = False
            reasons.append("not enough results")
        if extraction["avg_confidence"] < float(thresholds.get("min_extraction_confidence", 0.0)):
            passed = False
            reasons.append("confidence below threshold")
        if count_retries(state.retry_attempts or []) > int(thresholds.get("max_retry_count", 999)):
            passed = False
            reasons.append("retry count above threshold")
        if selection["precision"] < float(thresholds.get("min_skill_precision", 0.0)):
            passed = False
            reasons.append("skill precision below threshold")
        if selection["recall"] < float(thresholds.get("min_skill_recall", 0.0)):
            passed = False
            reasons.append("skill recall below threshold")

        report = {
            "query": case["query"],
            "category": case.get("category", "unknown"),
            "passed": passed,
            "reasons": reasons,
            "selection": selection,
            "extraction": extraction,
            "reliability": reliability,
            "selected_skills": state.selected_skills,
            "result_count": len(rows),
            "workflow_status": state.workflow_status,
        }
        case_reports.append(report)
        if not passed:
            failures.append(report)

    summary = {
        "cases": len(case_reports),
        "passed_cases": sum(1 for item in case_reports if item["passed"]),
        "avg_skill_precision": round(sum(item["selection"]["precision"] for item in case_reports) / max(1, len(case_reports)), 2),
        "avg_skill_recall": round(sum(item["selection"]["recall"] for item in case_reports) / max(1, len(case_reports)), 2),
        "avg_skill_f1": round(sum(item["selection"]["f1_score"] for item in case_reports) / max(1, len(case_reports)), 2),
        "avg_extraction_success_rate": round(sum(item["extraction"]["extraction_success_rate"] for item in case_reports) / max(1, len(case_reports)), 2),
        "avg_confidence": round(sum(item["extraction"]["avg_confidence"] for item in case_reports) / max(1, len(case_reports)), 2),
        "avg_reliability_score": round(sum(item["reliability"]["reliability_score"] for item in case_reports) / max(1, len(case_reports)), 2),
    }
    payload = {"summary": summary, "cases": case_reports, "failures": failures, "thresholds": thresholds}
    payload["report_paths"] = _write_reports(payload)

    print(json.dumps(payload, indent=2, default=str))
    return 0 if not failures else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
