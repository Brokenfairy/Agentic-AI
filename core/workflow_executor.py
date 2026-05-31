"""Phase 6 workflow executor."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from config import settings
from core.agent_collaboration import CollaborationBus, suggest_collaboration
from core.checkpoints import save_checkpoint
from core.compare_mode import compare_extraction
from core.comparison_engine import compare_results
from core.deep_supervisor import run_supervisor
from core.extractor_engine import extract_fields
from core.failure_simulator import simulation_flags
from core.logger import get_logger
from core.query_parser import parse_query
from core.recovery_engine import count_retries, retry_operation
from core.result_aggregator import aggregate_results
from core.tool_registry import discover_tools
from core.workflow_replay import save_trace
from core.workflow_state import WorkflowState, new_state
from core.workflow_summary import build_summary
from database.db import init_db, save_workflow_run
from evals.metrics import extraction_metrics
from evals.reliability import reliability_metrics
from exports import export_csv, export_excel, export_json, export_markdown
from langfuse_config import LangfuseTracker, mask_sensitive
from reports import generate_run_reports
from tools.page_reader import read_page
from tools.web_search_tool import search_web


EventCallback = Callable[[Dict[str, Any]], None]

FIELD_BY_AGENT = {
    "price_extractor": ["price", "discount", "best_deal", "seller_trust"],
    "rating_extractor": ["rating", "seller_trust"],
    "availability_extractor": ["availability", "availability_confidence", "delivery_estimate"],
    "specs_extractor": ["specs", "warranty"],
    "location_extractor": ["location"],
}


def _load_cache_file(filename: str) -> Any:
    try:
        return json.loads((settings.DEMO_CACHE_DIR / filename).read_text(encoding="utf-8"))
    except Exception:
        return None


def _cached_urls(limit: int) -> List[Dict[str, Any]]:
    payload = _load_cache_file("sample_urls.json") or []
    return payload[:limit] if isinstance(payload, list) else []


def _cached_extraction_for(url: str) -> Dict[str, Any]:
    payload = _load_cache_file("sample_extractions.json") or {}
    if not isinstance(payload, dict):
        return {}
    return payload.get(url) or payload.get("default") or {}


def _emit_progress(state: WorkflowState, logger, *, stage_name: str, index: int, total: int) -> None:
    state.current_node = stage_name
    state.current_skill = stage_name
    state.progress_percent = round((index / max(1, total)) * 100, 1)
    state.progress_message = f"Running {stage_name.replace('_', ' ')}"
    logger.event(
        "progress_update",
        stage=stage_name,
        progress_percent=state.progress_percent,
        progress_message=state.progress_message,
    )


def _classify_query(query: str) -> str:
    lowered = (query or "").lower()
    if any(term in lowered for term in ("restaurant", "food", "cafe", "dining")):
        return "restaurants"
    if any(term in lowered for term in ("hotel", "stay", "booking", "resort")):
        return "hotels"
    if any(term in lowered for term in ("laptop", "gaming", "notebook")):
        return "laptops"
    if any(term in lowered for term in ("iphone", "phone", "mobile", "electronics")):
        return "ecommerce"
    if any(term in lowered for term in ("market", "competitor", "compare", "pricing")):
        return "market_comparison"
    return "general"


def _record_replay_frame(state: WorkflowState, label: str) -> None:
    rows = ((state.aggregated_results or {}).get("rows") or []) if state.aggregated_results else []
    state.replay_frames.append(
        {
            "label": label,
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "progress_percent": state.progress_percent,
            "current_node": state.current_node,
            "selected_skills": list(state.selected_skills),
            "completed_nodes": list(state.completed_nodes),
            "failed_nodes": list(state.failed_nodes),
            "partial_results": rows[:5],
            "supervisor_thoughts": list(state.supervisor_thoughts[:6]),
            "trace_id": state.trace_id,
            "trace_url": state.trace_url,
        }
    )


def _build_traceability(state: WorkflowState) -> None:
    state.traceability_chain = []
    state.skill_docs_used = []
    for skill in state.selected_skills:
        meta = (state.available_agents or {}).get(skill) or {}
        chain_item = {
            "skill": skill,
            "yaml_path": meta.get("yaml_path", ""),
            "skill_doc_path": meta.get("skill_doc_path", ""),
            "model": (meta.get("model") or {}).get("name", ""),
            "provider": (meta.get("model") or {}).get("provider", ""),
            "dependencies": meta.get("dependencies", []),
        }
        state.traceability_chain.append(chain_item)
        if meta.get("skill_doc_path"):
            state.skill_docs_used.append(
                {"skill": skill, "path": meta.get("skill_doc_path", "")}
            )


def _finalize_health(state: WorkflowState) -> None:
    expected_fields = list((state.parsed_query or {}).get("requested_fields") or [])
    rows = ((state.aggregated_results or {}).get("rows") or []) if state.aggregated_results else []
    state.extraction_quality = extraction_metrics(rows, expected_fields)
    state.workflow_health = reliability_metrics(state)
    state.health_score = float(state.workflow_health.get("reliability_score") or 0.0)
    state.evaluation_scores = {
        "extraction_quality": state.extraction_quality,
        "reliability": state.workflow_health,
    }
    state.failed_spans = list(state.failed_nodes)
    state.langfuse_metrics = {
        "span_count": len(state.execution_times),
        "failed_span_count": len(state.failed_spans),
        "avg_execution_latency": round(
            sum(float(value) for value in state.execution_times.values()) / max(1, len(state.execution_times)),
            3,
        ),
    }
    if not state.token_usage:
        state.token_usage = {
            "prompt_count": len(state.prompts_used),
            "estimated_total_tokens": max(0, len(json.dumps(state.plan or {})) // 4),
        }


def _run_stage(
    *,
    name: str,
    fn: Callable[[WorkflowState, Any], None],
    state: WorkflowState,
    logger,
    tracker: LangfuseTracker,
    stage_index: int,
    total_stages: int,
    span_input: Optional[Dict[str, Any]] = None,
    span_output_builder: Optional[Callable[[WorkflowState], Dict[str, Any]]] = None,
) -> bool:
    _emit_progress(state, logger, stage_name=name, index=stage_index, total=total_stages)
    state.workflow_status = "running"
    logger.event("node_start", node=name, input=span_input or {})

    span_id = tracker.start_span(name, input=span_input or {})
    t0 = time.perf_counter()
    success = True
    error_message: Optional[str] = None

    try:
        fn(state, logger)
    except Exception as exc:
        success = False
        error_message = f"{type(exc).__name__}: {exc}"
        state.add_error(f"[{name}] {error_message}")
        logger.error(f"Node {name} failed: {error_message}")
        if True:
            elapsed = round(time.perf_counter() - t0, 3)
            state.execution_times[name] = elapsed
            state.failed_nodes.append(name)
            tracker.end_span(span_id, level="ERROR", status_message=error_message, output={"error": error_message})
            logger.event("node_end", node=name, status="failed", error=error_message, duration=elapsed)
            checkpoint_path = save_checkpoint(state, name)
            state.checkpoint_paths.append(checkpoint_path)
            state.latest_checkpoint_path = checkpoint_path
            raise

    elapsed = round(time.perf_counter() - t0, 3)
    state.execution_times[name] = elapsed
    if span_output_builder is not None:
        try:
            state.skill_outputs[name] = span_output_builder(state)
        except Exception:
            state.skill_outputs[name] = {}

    if success:
        if name not in state.completed_nodes:
            state.completed_nodes.append(name)
        tracker.end_span(span_id, output=state.skill_outputs.get(name) or {}, level="DEFAULT")
        logger.event(
            "node_end",
            node=name,
            status="completed",
            duration=elapsed,
            output=state.skill_outputs.get(name) or {},
        )
    else:
        if name not in state.failed_nodes:
            state.failed_nodes.append(name)
        tracker.end_span(span_id, output={"error": error_message}, level="ERROR", status_message=error_message)
        logger.event("node_end", node=name, status="failed", error=error_message, duration=elapsed)

    checkpoint_path = save_checkpoint(state, name)
    state.checkpoint_paths.append(checkpoint_path)
    state.latest_checkpoint_path = checkpoint_path
    _record_replay_frame(state, name)
    return success


def _stage_query_understanding(state: WorkflowState, logger) -> None:
    state.parsed_query = parse_query(state.original_query)
    logger.success(
        f"Parsed query into search='{state.parsed_query.get('search_query', '')}' "
        f"and fields={state.parsed_query.get('requested_fields', [])}."
    )


def _stage_supervisor(state: WorkflowState, logger) -> None:
    started = time.perf_counter()
    run_supervisor(state)
    state.planning_latency_ms = round((time.perf_counter() - started) * 1000, 2)
    state.query_category = _classify_query(state.original_query)
    _build_traceability(state)
    state.prompts_used.append(
        {
            "stage": "planner",
            "provider": state.provider_name,
            "model": state.provider_model,
            "prompt_type": "execution_plan",
        }
    )
    logger.success(f"Supervisor generated a {state.supervisor_backend} plan with {len(state.selected_skills)} skills.")
    for thought in state.supervisor_thoughts[:6]:
        logger.event("supervisor_thought", message=thought)
    for line in state.supervisor_reasoning[:8]:
        logger.info(line)


def _stage_url_scraper(state: WorkflowState, logger) -> None:
    if "url_scraper" not in state.selected_skills:
        logger.info("Skipping url_scraper because it was not selected.")
        return

    parsed_query = state.parsed_query or {}
    search_limit = parsed_query.get("limit", settings.DEFAULT_URL_LIMIT)
    result = search_web(
        parsed_query.get("search_query", "") or state.original_query,
        limit=search_limit,
        allow_mock=False,
    )
    urls = result.get("results") or []
    if not urls:
        state.cached_data_used = True

    state.scraped_urls = urls
    if state.scraped_urls:
        logger.success(f"Discovered {len(state.scraped_urls)} URL(s).")
    else:
        logger.warning("No URLs were discovered.")


def _stage_page_reader(state: WorkflowState, logger) -> None:
    extractor_skills = [name for name in state.selected_skills if name.endswith("_extractor")]
    if not extractor_skills or not state.scraped_urls:
        logger.info("Skipping page_reader because there are no extractor stages or URLs.")
        return

    workers = max(1, min(settings.PARALLEL_PAGE_READS, 8))
    logger.info(f"Reading {len(state.scraped_urls)} pages with max_workers={workers}.")

    def _read_with_retry(url_entry: Dict[str, Any]) -> Dict[str, Any]:
        url = url_entry.get("url", "")
        result, attempts = retry_operation(lambda: read_page(url), label=f"read:{url}")
        return {"page": result, "attempts": attempts, "url_entry": url_entry}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_read_with_retry, url_entry): url_entry for url_entry in state.scraped_urls}
        for future in as_completed(future_map):
            outcome = future.result()
            page = outcome["page"]
            attempts = outcome["attempts"]
            url_entry = outcome["url_entry"]
            url = url_entry.get("url", "")
            domain = url_entry.get("domain", "")

            state.retry_attempts.extend(attempts)
            state.page_cache[url] = page
            state.page_reads.append(
                {
                    "url": url,
                    "domain": domain,
                    "status": page.get("status", "failed"),
                    "method": page.get("method", ""),
                    "title": page.get("title", ""),
                    "error": page.get("error", ""),
                }
            )
            if page.get("status") != "success":
                state.failed_urls.append(
                    {"url": url, "domain": domain, "error": page.get("error", "unknown error")}
                )
                state.recovery_actions.append({"kind": "page_retry", "url": url, "attempts": attempts})
                logger.warning(f"Page read failed for {url}: {page.get('error', 'unknown error')}")
                logger.event("page_read", url=url, domain=domain, status="failed", error=page.get("error", ""))
            else:
                logger.event("page_read", url=url, domain=domain, status="success", method=page.get("method", ""))


def _get_or_create_record(state: WorkflowState, url_entry: Dict[str, Any]) -> Dict[str, Any]:
    url = url_entry.get("url", "")
    for record in state.extracted_data:
        if record.get("url") == url:
            return record
    record = {
        "url": url,
        "title": url_entry.get("title", ""),
        "domain": url_entry.get("domain", ""),
        "fields": {},
        "fallback_used": False,
        "confidence_score": 0.0,
        "page_method": "",
        "status": "success",
        "source_agents": [],
    }
    state.extracted_data.append(record)
    return record


def _extract_task(
    *,
    agent_name: str,
    url_entry: Dict[str, Any],
    page: Dict[str, Any],
    heuristic_mode: bool,
) -> Dict[str, Any]:
    requested_fields = FIELD_BY_AGENT.get(agent_name) or []
    page_meta = {
        "title": page.get("title") or url_entry.get("title", ""),
        "metadata": page.get("metadata", {}),
        "domain": url_entry.get("domain", ""),
    }
    text = page.get("content", "") if page.get("status") == "success" else ""
    extraction, attempts = retry_operation(
        lambda: {
            "status": "success",
            **extract_fields(
                text,
                requested_fields,
                page_meta=page_meta,
                allow_fallback=False,
                use_llm=not heuristic_mode,
            ),
        },
        label=f"extract:{agent_name}:{url_entry.get('url', '')}",
    )
    return {
        "agent_name": agent_name,
        "url_entry": url_entry,
        "page": page,
        "extraction": extraction,
        "attempts": attempts,
        "requests": suggest_collaboration(agent_name, extraction.get("fields", {})),
    }


def _stage_parallel_extractors(state: WorkflowState, logger) -> None:
    extractor_skills = [name for name in state.selected_skills if name.endswith("_extractor")]
    if not extractor_skills or not state.scraped_urls:
        logger.info("Skipping extractors because no extractor agents are selected.")
        return

    collaboration = CollaborationBus()
    state.collaboration_memory = collaboration.snapshot()
    workers = max(1, min(settings.AGENT_PARALLELISM, len(extractor_skills) * max(1, len(state.scraped_urls))))

    tasks = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for agent_name in extractor_skills:
            for url_entry in state.scraped_urls:
                page = state.page_cache.get(url_entry.get("url", "")) or {}
                tasks.append(
                    pool.submit(
                        _extract_task,
                        agent_name=agent_name,
                        url_entry=url_entry,
                        page=page,
                        heuristic_mode=state.heuristic_mode,
                    )
                )

        for future in as_completed(tasks):
            outcome = future.result()
            agent_name = outcome["agent_name"]
            url_entry = outcome["url_entry"]
            page = outcome["page"]
            extraction = outcome["extraction"]
            state.retry_attempts.extend(outcome["attempts"])

            record = _get_or_create_record(state, url_entry)
            record["title"] = page.get("title") or record.get("title", "")
            record["page_method"] = page.get("method", "")
            record["fallback_used"] = bool(record.get("fallback_used") or extraction.get("fallback_used"))
            record["confidence_score"] = max(
                float(record.get("confidence_score") or 0.0),
                float(extraction.get("confidence_score") or 0.0),
            )
            record["status"] = "fallback" if record["fallback_used"] else "success"
            record.setdefault("source_agents", []).append(agent_name)
            record["fields"].update(extraction.get("fields") or {})

            if extraction.get("semantic_enabled"):
                state.semantic_extraction_enabled = True
            if extraction.get("fallback_used"):
                state.fallback_used = True
            if not any(
                prompt.get("stage") == "extractor" and prompt.get("agent") == agent_name
                for prompt in state.prompts_used
            ):
                state.prompts_used.append(
                    {
                        "stage": "extractor",
                        "agent": agent_name,
                        "provider": state.provider_name,
                        "model": state.provider_model,
                        "fields": FIELD_BY_AGENT.get(agent_name, []),
                    }
                )

            collaboration.publish_output(
                agent_name,
                {
                    "url": url_entry.get("url", ""),
                    "fields": extraction.get("fields", {}),
                    "confidence_score": extraction.get("confidence_score", 0.0),
                },
            )
            for request in outcome["requests"]:
                item = collaboration.request_validation(
                    agent_name,
                    request["target_agent"],
                    {
                        "url": url_entry.get("url", ""),
                        "reason": request["reason"],
                        "fields": extraction.get("fields", {}),
                    },
                )
                state.validation_requests.append(item)

            state.collaboration_memory = collaboration.snapshot()
            state.collaboration_messages = state.collaboration_memory.get("messages", [])
            logger.success(
                f"{agent_name} extracted fields from {url_entry.get('domain', url_entry.get('url', ''))} "
                f"(method={extraction.get('method')}, conf={extraction.get('confidence_score')})."
            )
            logger.event(
                "partial_result",
                agent=agent_name,
                url=url_entry.get("url", ""),
                fields=extraction.get("fields", {}),
                confidence_score=extraction.get("confidence_score", 0.0),
            )


def _stage_aggregation(state: WorkflowState, logger) -> None:
    state.aggregated_results = aggregate_results(state)
    logger.success(f"Aggregated {len((state.aggregated_results or {}).get('rows') or [])} rows.")


def _stage_comparison_engine(state: WorkflowState, logger) -> None:
    if "comparison_engine" not in state.selected_skills:
        logger.info("Skipping comparison_engine because it was not selected.")
        return
    rows = (state.aggregated_results or {}).get("rows") or []
    state.comparison_results = compare_results(rows)
    logger.success("Generated structured comparison report.")


def _stage_compare_mode(state: WorkflowState, logger) -> None:
    if not state.page_cache or not state.parsed_query.get("requested_fields"):
        logger.info("Skipping compare_mode because there is no page content to compare.")
        return
    for url_entry in state.scraped_urls:
        page = state.page_cache.get(url_entry.get("url", "")) or {}
        if page.get("status") != "success":
            continue
        state.comparison_results.setdefault(
            "quality_comparison",
            compare_extraction(
                page.get("content", ""),
                state.parsed_query.get("requested_fields") or [],
                page_meta={"title": page.get("title", ""), "metadata": page.get("metadata", {})},
            ),
        )
        logger.info("Computed heuristic vs Gemini comparison on a sampled page.")
        return


def _stage_exports(state: WorkflowState, logger) -> None:
    rows = (state.aggregated_results or {}).get("rows") or []
    summary = (state.aggregated_results or {}).get("summary") or {}
    if not rows:
        logger.warning("Skipping exports because there are no rows.")
        return

    provisional_summary = (
        f"Rows: {len(rows)} | Success: {summary.get('success_count', 0)} | "
        f"Fallback: {summary.get('fallback_count', 0)} | Failed: {summary.get('failed_count', 0)}"
    )
    excel_result = export_excel(rows, query=state.original_query)
    csv_result = export_csv(rows, query=state.original_query)
    json_result = export_json(rows, query=state.original_query, summary=summary)
    markdown_result = export_markdown(rows, query=state.original_query, summary=state.ai_summary or state.summary_markdown or provisional_summary)

    state.excel_path = excel_result.get("excel_path") or None
    state.rows_written = int(excel_result.get("rows_written") or len(rows))
    state.export_paths = {
        "excel": excel_result.get("excel_path", ""),
        "csv": csv_result.get("csv_path", ""),
        "json": json_result.get("json_path", ""),
        "markdown": markdown_result.get("markdown_path", ""),
    }
    state.artifacts_generated.extend(
        artifact
        for artifact in ["Excel Report", "CSV Export", "JSON Export", "Markdown Report"]
        if artifact not in state.artifacts_generated
    )
    logger.success("Generated Excel, CSV, JSON, and Markdown outputs.")


def _snapshot_plan(state: WorkflowState) -> Dict[str, Any]:
    return {
        "goal": state.plan_goal,
        "steps": state.plan_steps,
        "selected_skills": state.selected_skills,
    }


def _snapshot_page_reader(state: WorkflowState) -> Dict[str, Any]:
    return {
        "success_pages": sum(1 for item in state.page_reads if item.get("status") == "success"),
        "failed_pages": len(state.failed_urls),
            "retry_attempts": count_retries(state.retry_attempts),
    }


def _snapshot_extractors(state: WorkflowState) -> Dict[str, Any]:
    return {
        "records": len(state.extracted_data),
        "fallback_used": state.fallback_used,
        "semantic_enabled": state.semantic_extraction_enabled,
        "collaboration_messages": len(state.collaboration_messages),
    }


def _snapshot_aggregation(state: WorkflowState) -> Dict[str, Any]:
    return (state.aggregated_results or {}).get("summary") or {}


def _snapshot_comparison(state: WorkflowState) -> Dict[str, Any]:
    return state.comparison_results


def _snapshot_exports(state: WorkflowState) -> Dict[str, Any]:
    return state.export_paths


def run_workflow(
    query: str,
    *,
    on_event: Optional[EventCallback] = None,
    state: Optional[WorkflowState] = None,
    enable_excel: bool = True,
    enable_compare: bool = True,
) -> WorkflowState:
    state = state or new_state(
        query,
        user_id=settings.LANGFUSE_USER_ID or None,
        session_id=settings.LANGFUSE_SESSION_ID or None,
        tags=settings.LANGFUSE_TAGS or [],
    )
    logger = get_logger(state, on_event=on_event)
    tracker = LangfuseTracker(
        state,
        name="skillflow.phase6",
        user_id=state.user_id,
        session_id=state.session_id,
        tags=state.tags,
    )
    state._langfuse_tracker = tracker
    state.trace_url = tracker.trace_url
    state.available_tools = discover_tools()
    state.simulation_flags = simulation_flags()
    init_db()

    state.workflow_status = "running"
    state.workflow_start_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    start = time.perf_counter()

    logger.event(
        "workflow_start",
        query=query,
        trace_id=state.trace_id,
        trace_url=state.trace_url,
        simulation_flags=state.simulation_flags,
    )
    _record_replay_frame(state, "workflow_start")

    initial_stages: List[tuple[str, Callable[[WorkflowState, Any], None], Callable[[WorkflowState], Dict[str, Any]]]] = [
        ("query_understanding", _stage_query_understanding, lambda current: {"parsed_query": current.parsed_query}),
        ("supervisor", _stage_supervisor, _snapshot_plan),
    ]

    for index, (name, fn, snapshot) in enumerate(initial_stages, start=1):
        _run_stage(
            name=name,
            fn=fn,
            state=state,
            logger=logger,
            tracker=tracker,
            stage_index=index,
            total_stages=max(2, len(initial_stages)),
            span_input={"query": query, "selected_skills": state.selected_skills},
            span_output_builder=snapshot,
        )

    stages: List[tuple[str, Callable[[WorkflowState, Any], None], Callable[[WorkflowState], Dict[str, Any]]]] = [
        ("url_scraper", _stage_url_scraper, lambda current: {"url_count": len(current.scraped_urls)}),
        ("page_reader", _stage_page_reader, _snapshot_page_reader),
        ("parallel_extractors", _stage_parallel_extractors, _snapshot_extractors),
        ("aggregation", _stage_aggregation, _snapshot_aggregation),
    ]
    if "comparison_engine" in state.selected_skills:
        stages.append(("comparison_engine", _stage_comparison_engine, _snapshot_comparison))
    if enable_compare:
        stages.append(("compare_mode", _stage_compare_mode, _snapshot_comparison))
    if enable_excel:
        stages.append(("exports", _stage_exports, _snapshot_exports))

    total_stages = len(initial_stages) + len(stages)
    for offset, (name, fn, snapshot) in enumerate(stages, start=len(initial_stages) + 1):
        _run_stage(
            name=name,
            fn=fn,
            state=state,
            logger=logger,
            tracker=tracker,
            stage_index=offset,
            total_stages=total_stages,
            span_input={"query": query, "selected_skills": state.selected_skills},
            span_output_builder=snapshot,
        )

    state.workflow_end_time = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    state.total_duration_seconds = round(time.perf_counter() - start, 3)
    state.current_node = ""
    state.current_skill = ""
    state.progress_percent = 100.0
    state.progress_message = "Workflow completed"
    state.workflow_status = "completed" if not state.failed_nodes else "failed"

    _finalize_health(state)
    summary_block = build_summary(state)
    state.summary_markdown = summary_block["markdown"]
    state.ai_summary = summary_block.get("ai_summary", "")

    if state.trace_url and "Langfuse Trace" not in state.artifacts_generated:
        state.artifacts_generated.append("Langfuse Trace")
    state.trace_path = save_trace(state)
    state.replay_trace_path = state.trace_path
    if "Workflow Log" not in state.artifacts_generated:
        state.artifacts_generated.append("Workflow Log")
    if "Checkpoint Trail" not in state.artifacts_generated:
        state.artifacts_generated.append("Checkpoint Trail")
    state.report_paths = generate_run_reports(state)
    state.artifacts_generated.extend(
        artifact
        for artifact in ["Workflow Report", "Reliability Report", "Extraction Quality Report"]
        if artifact not in state.artifacts_generated
    )

    state.db_run_id = save_workflow_run(state)
    state.persisted = True

    tracker.end(
        output={
            "query": state.original_query,
            "plan": state.plan,
            "selected_skills": state.selected_skills,
            "skipped_skills": state.skipped_skills,
            "reasoning": state.supervisor_reasoning,
            "supervisor_thoughts": state.supervisor_thoughts,
            "urls": state.scraped_urls,
            "extraction_results": state.extracted_data,
            "comparison_results": state.comparison_results,
            "workflow_timings": state.execution_times,
            "failures": state.failed_urls,
            "fallback_usage": state.fallback_used,
            "retry_attempts": state.retry_attempts,
            "exports": state.export_paths,
            "checkpoints": state.checkpoint_paths,
            "db_run_id": state.db_run_id,
            "query_category": state.query_category,
            "planning_latency_ms": state.planning_latency_ms,
            "health_score": state.health_score,
            "workflow_health": state.workflow_health,
            "extraction_quality": state.extraction_quality,
            "evaluation_scores": state.evaluation_scores,
            "traceability_chain": state.traceability_chain,
            "report_paths": state.report_paths,
        }
    )

    logger.success(f"Workflow {state.workflow_status} in {state.total_duration_seconds}s.")
    logger.event(
        "workflow_end",
        status=state.workflow_status,
        duration=state.total_duration_seconds,
        trace_path=state.trace_path,
        db_run_id=state.db_run_id,
        export_paths=state.export_paths,
    )
    return state
