"""Generate workflow summaries, optionally with Gemini."""

from __future__ import annotations

from typing import Any, Dict

from config import settings
from core.llm_provider import build_llm
from core.recovery_engine import count_retries
from core.workflow_state import WorkflowState
from schemas import WorkflowSummary


def _humanize(seconds: float) -> str:
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    rest = seconds - (minutes * 60)
    return f"{minutes}m {rest:.0f}s"


def _build_template_summary(state: WorkflowState, summary: WorkflowSummary) -> str:
    comparison = state.comparison_results or {}
    lowest = ((comparison.get("lowest_price") or {}) if isinstance(comparison, dict) else {}) or {}
    highest = ((comparison.get("highest_rating") or {}) if isinstance(comparison, dict) else {}) or {}
    parts = [
        f"The system discovered {summary.total_urls} product URL(s).",
        f"{summary.success_count} successful extraction(s) were completed.",
        f"{summary.fallback_count} extraction(s) used fallback logic.",
    ]
    if lowest:
        parts.append(f"{lowest.get('domain', 'One source')} offered the lowest visible price.")
    if highest:
        parts.append(f"{highest.get('domain', 'One source')} had the highest visible rating.")
    return " ".join(parts)


def _build_ai_summary(state: WorkflowState, template_summary: str) -> str:
    llm = build_llm()
    if llm is None:
        return template_summary
    try:
        prompt = (
            "Write a concise executive workflow summary in 4 short sentences.\n"
            "Mention discovered URLs, extraction success, fallback usage, and key comparison insights.\n"
            f"Query: {state.original_query}\n"
            f"Selected Skills: {state.selected_skills}\n"
            f"Comparison Results: {state.comparison_results}\n"
            f"Template Summary: {template_summary}\n"
        )
        response = llm.invoke(prompt)
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "\n".join(str(part) for part in content)
        text = str(content).strip()
        return text or template_summary
    except Exception:
        return template_summary


def build_summary(state: WorkflowState) -> Dict[str, Any]:
    aggregated = state.aggregated_results or {}
    summary_data = aggregated.get("summary") or {}
    skipped_names = [item.get("name", "") for item in state.skipped_skills if item.get("name")]

    summary = WorkflowSummary(
        query=state.original_query,
        search_query=state.parsed_query.get("search_query", ""),
        requested_fields=list(state.parsed_query.get("requested_fields") or []),
        selected_skills=list(state.selected_skills),
        skipped_skills=skipped_names,
        total_urls=int(summary_data.get("total_urls") or len(state.scraped_urls)),
        success_count=int(summary_data.get("success_count") or 0),
        fallback_count=int(summary_data.get("fallback_count") or 0),
        failed_count=int(summary_data.get("failed_count") or len(state.failed_urls)),
        total_duration_seconds=float(state.total_duration_seconds or 0.0),
        excel_path=state.excel_path,
        trace_id=state.trace_id,
        trace_url=state.trace_url,
        workflow_status=state.workflow_status,
        supervisor_backend=state.supervisor_backend,
        provider_name=state.provider_name,
        provider_model=state.provider_model,
        artifacts_generated=list(state.artifacts_generated),
        plan_goal=state.plan_goal,
        retry_count=count_retries(state.retry_attempts),
        top_domains=list(summary_data.get("top_domains") or []),
    )

    template_summary = _build_template_summary(state, summary)
    ai_summary = _build_ai_summary(state, template_summary)

    selected_lines = "\n".join(f"- `{skill}`" for skill in state.selected_skills) or "- None"
    artifact_lines = "\n".join(f"- {artifact}" for artifact in state.artifacts_generated) or "- Workflow Log"

    markdown = f"""
### Workflow Execution Summary

**Query:**  
{summary.query}

**Supervisor Thought Process:**  
{chr(10).join(f"- {thought}" for thought in state.supervisor_thoughts[:6]) or "- No thoughts recorded"}

**Supervisor Selected Skills:**  
{selected_lines}

**Execution Results:**  
- {summary.total_urls} URL(s) discovered
- {summary.success_count} successful extraction(s)
- {summary.fallback_count} fallback extraction(s)
- {summary.failed_count} failed page read(s)
- {summary.retry_count} retry attempt(s) triggered
- Top domains: {", ".join(summary.top_domains) if summary.top_domains else "n/a"}
- Provider path: `{summary.provider_name or 'heuristic'}` / `{summary.provider_model or 'none'}`
- Supervisor backend: `{summary.supervisor_backend}`
- Query category: `{state.query_category or 'general'}`
- Planning latency: **{state.planning_latency_ms:.0f}ms**
- Health score: **{state.health_score:.2f}**
- Total duration: **{_humanize(summary.total_duration_seconds)}**

**AI Summary:**  
{ai_summary}

**Artifacts Generated:**  
{artifact_lines}

**Traceability:**  
- YAML configs: {len(state.traceability_chain)}
- Skill docs referenced: {len(state.skill_docs_used)}
""".strip()

    return {"summary": summary, "markdown": markdown, "ai_summary": ai_summary}
