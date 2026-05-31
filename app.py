"""SkillFlow AI Phase 6 Streamlit application."""

from __future__ import annotations

import json
from copy import deepcopy

import streamlit as st

from components import (
    render_agent_performance,
    render_analytics_dashboard,
    render_architecture_diagram,
    render_dependency_graph,
    render_execution_timeline,
    render_langfuse_dashboard,
    render_metrics_dashboard,
    render_observability_panel,
    render_presentation_dashboard,
    render_skill_cards,
    render_skill_markdown_viewer,
    render_supervisor_analytics,
    render_supervisor_reasoning,
    render_supervisor_thoughts,
    render_workflow_health,
    render_workflow_graph,
    render_workflow_history,
    render_yaml_editor,
)
from config import settings
from core.agent_loader import load_all_agents
from core.llm_provider import provider_status
from core.marketplace_loader import load_marketplace_packs
from core.workflow_executor import run_workflow
from core.workflow_replay import list_replayables, replay_trace
from startup_checks import run_startup_checks


st.set_page_config(page_title="SkillFlow AI", page_icon="SF", layout="wide")


st.markdown(
    """
<style>
.block-container {padding-top: 1rem; padding-bottom: 1.5rem;}
.hero {
  padding: 1.2rem 1.4rem;
  border: 1px solid rgba(148,163,184,.22);
  border-radius: 18px;
  background:
    radial-gradient(circle at top left, rgba(16,185,129,.16), transparent 28%),
    radial-gradient(circle at top right, rgba(59,130,246,.18), transparent 32%),
    linear-gradient(135deg, rgba(15,23,42,.98), rgba(30,41,59,.92));
  color: white;
  margin-bottom: 1rem;
}
.sticky-panel {
  position: sticky;
  top: 1rem;
  z-index: 10;
  padding: .8rem 1rem;
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,.2);
  background: rgba(15,23,42,.88);
  color: white;
  margin-bottom: 1rem;
}
.badge-row {display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.4rem;}
.badge {
  display:inline-block;
  padding:.18rem .55rem;
  border-radius:999px;
  font-size:.78rem;
  border:1px solid rgba(255,255,255,.18);
  background: rgba(255,255,255,.08);
}
</style>
""",
    unsafe_allow_html=True,
)




def _format_event_line(evt: dict) -> str:
    ts = evt.get("ts_short", "")
    kind = evt.get("kind", "")
    if kind == "log":
        return f"[{ts}] [{evt.get('level', 'INFO')}] {evt.get('message', '')}"
    if kind == "node_start":
        return f"[{ts}] Entering {evt.get('node', '')}"
    if kind == "node_end":
        return f"[{ts}] Finished {evt.get('node', '')} ({evt.get('status', '')})"
    if kind == "supervisor_thought":
        return f"[{ts}] Thought: {evt.get('message', '')}"
    if kind == "partial_result":
        return f"[{ts}] Partial result from {evt.get('agent', '')} -> {evt.get('url', '')}"
    if kind == "progress_update":
        return f"[{ts}] {evt.get('progress_message', '')} ({evt.get('progress_percent', 0)}%)"
    return f"[{ts}] {kind}"


def _render_compare(state: dict) -> None:
    comparison = state.get("comparison_results") or {}
    if not comparison:
        st.info("No comparison output yet.")
        return
    if "quality_comparison" in comparison:
        quality = comparison["quality_comparison"]
        c1, c2 = st.columns(2)
        heuristic = quality.get("heuristic") or {}
        gemini = quality.get("gemini") or {}
        c1.metric("Heuristic Quality", heuristic.get("quality", 0.0))
        c1.metric("Heuristic Timing", f"{heuristic.get('timing_ms', 0)}ms")
        c2.metric("Gemini Quality", gemini.get("quality", 0.0))
        c2.metric("Gemini Timing", f"{gemini.get('timing_ms', 0)}ms")
    st.json(comparison, expanded=False)


def _render_results_table(state: dict) -> None:
    rows = (state.get("aggregated_results") or {}).get("rows") or []
    summary = (state.get("aggregated_results") or {}).get("summary") or {}
    if not rows:
        st.info("No extraction rows yet.")
        return

    cols = st.columns(5)
    cols[0].metric("URLs Found", summary.get("total_urls", 0))
    cols[1].metric("Successful", summary.get("success_count", 0))
    cols[2].metric("Failed", summary.get("failed_count", 0))
    cols[3].metric("Fallback", summary.get("fallback_count", 0))
    cols[4].metric("Avg Confidence", f"{summary.get('avg_confidence', 0.0):.2f}")

    st.divider()

    df_cols = [c for c in list(rows[0].keys()) if c not in ("status", "fallback_used", "confidence_score", "_raw")]
    display_cols = ["url", "title", "domain", "status", "confidence_score"] + [c for c in df_cols if c not in ("url", "title", "domain", "status", "confidence_score")]
    display_cols = [c for c in display_cols if c in rows[0]]

    st.dataframe(
        [{k: r.get(k, "") for k in display_cols} for r in rows],
        use_container_width=True,
        hide_index=True,
    )


def _render_state(state: dict, *, catalog: dict, live_logs: list[str] | None, placeholders: dict | None = None) -> None:
    live_logs = live_logs or state.get("logs") or []

    provider = state.get("provider_name") or "heuristic"
    model = state.get("provider_model") or "none"
    status = (state.get("workflow_status") or "idle").upper()
    progress = state.get("progress_percent", 0.0)
    progress_message = state.get("progress_message", "Idle")

    target = placeholders or {
        "sticky": st,
        "graph": st,
        "timeline": st,
        "thoughts": st,
        "reasoning": st,
        "logs": st,
        "obs": st,
        "cards": st,
        "partial": st,
    }

    target["sticky"].markdown(
        f"""
<div class="sticky-panel">
  <div><strong>Workflow Status:</strong> {status}</div>
  <div><strong>Progress:</strong> {progress_message} ({progress}%)</div>
  <div class="badge-row">
    <span class="badge">Provider: {provider}</span>
    <span class="badge">Model: {model}</span>
    <span class="badge">Supervisor: {state.get('supervisor_backend', 'heuristic')}</span>
    <span class="badge">Trace: {state.get('trace_id', '-')}</span>
    <span class="badge">DB Run: {state.get('db_run_id', '-')}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    with target["graph"].container():
        st.subheader("Workflow Graph")
        render_workflow_graph(state)
    with target["timeline"].container():
        st.subheader("Execution Timeline")
        render_execution_timeline(state)
    with target["thoughts"].container():
        st.subheader("Supervisor Thoughts")
        render_supervisor_thoughts(state)
    with target["reasoning"].container():
        st.subheader("Supervisor Reasoning")
        render_supervisor_reasoning(state)
    with target["logs"].container():
        st.subheader("Live Logs")
        st.code("\n".join(live_logs[-120:]) or "(no logs)", language="text")
    with target["obs"].container():
        st.subheader("Observability")
        render_observability_panel(state)
    with target["cards"].container():
        st.subheader("Agent Cards")
        render_skill_cards(state, skills_catalog=catalog)
    with target["partial"].container():
        st.subheader("Partial / Final Results")
        _render_results_table(state)


startup_status = run_startup_checks()


with st.sidebar:
    st.title("SkillFlow AI")
    st.caption("Autonomous AI agent orchestration platform prototype")

    status = provider_status()
    st.write("**Gemini Provider:**", "available" if status["available"] else "heuristic fallback")
    st.write("**Google API Key:**", "set" if status["has_key"] else "missing")
    st.write("**Default Model:**", f"`{settings.DEFAULT_MODEL}`")
    st.write("**Startup Checks:**", "passed" if startup_status.get("ok") else "needs attention")

    st.divider()
    st.subheader("Marketplace Packs")
    for pack in load_marketplace_packs():
        st.caption(f"{pack.get('name')}: {pack.get('description')}")

    st.divider()
    st.subheader("Replay Sources")
    replayables = list_replayables(limit=12)
    if replayables:
        replay_options = {
            f"{item['query']} [{item['status']}] ({item['source']})": item
            for item in replayables
        }
        replay_label = st.selectbox("Previous runs", list(replay_options.keys()))
        if st.button("Load Replay", use_container_width=True):
            item = replay_options[replay_label]
            st.session_state["last_state"] = replay_trace(item["path"], source=item["source"])
    else:
        st.caption("No saved runs yet.")

    st.divider()
    with st.expander("Startup Validation", expanded=False):
        st.json(startup_status, expanded=False)

    st.divider()
    st.subheader("Workflow History")
    render_workflow_history(
        on_replay=lambda run_id: st.session_state.update(
            {"last_state": replay_trace(str(run_id), source="database")}
        )
    )


st.markdown(
    """
<div class="hero">
  <h2 style="margin:0 0 .35rem 0;">SkillFlow AI</h2>
  <div>Autonomous planning, multi-agent collaboration, persistent workflow memory, semantic extraction, replay, analytics, and production-style orchestration patterns.</div>
</div>
""",
    unsafe_allow_html=True,
)


query_col, compare_col, run_col, clear_col = st.columns([6, 1.4, 1.3, 1.0], gap="small")
with query_col:
    query = st.text_input(
        "Query",
        value=st.session_state.get("query", ""),
        placeholder="Enter a query...",
        label_visibility="collapsed",
    )
with compare_col:
    enable_compare = st.toggle("Compare", value=True)
with run_col:
    run_clicked = st.button("Run Workflow", type="primary", use_container_width=True)
with clear_col:
    if st.button("Clear", use_container_width=True):
        for key in ("last_state", "query"):
            st.session_state.pop(key, None)
        st.rerun()


catalog = load_all_agents()

sticky_placeholder = st.empty()
left, right = st.columns([1.5, 1.1], gap="large")
with left:
    graph_placeholder = st.empty()
    timeline_placeholder = st.empty()
    thoughts_placeholder = st.empty()
    reasoning_placeholder = st.empty()
with right:
    obs_placeholder = st.empty()
    cards_placeholder = st.empty()
partial_placeholder = st.empty()
logs_placeholder = st.empty()

placeholders = {
    "sticky": sticky_placeholder,
    "graph": graph_placeholder,
    "timeline": timeline_placeholder,
    "thoughts": thoughts_placeholder,
    "reasoning": reasoning_placeholder,
    "logs": logs_placeholder,
    "obs": obs_placeholder,
    "cards": cards_placeholder,
    "partial": partial_placeholder,
}


if run_clicked:
    st.session_state["query"] = query
    if not query.strip():
        st.error("Enter a query before running the workflow.")
        st.stop()

    live_logs: list[str] = []
    live_state = {
        "workflow_status": "running",
        "logs": [],
        "progress_message": "Starting workflow",
        "progress_percent": 0.0,
        "selected_skills": [],
        "skipped_skills": [],
        "execution_plan": [],
        "workflow_events": [],
    }

    _render_state(live_state, catalog=catalog, live_logs=live_logs, placeholders=placeholders)

    def _merge_event_into_state(evt: dict) -> None:
        live_state.setdefault("workflow_events", []).append(evt)
        live_state["logs"] = live_logs
        if evt.get("kind") == "progress_update":
            live_state["progress_message"] = evt.get("progress_message", "")
            live_state["progress_percent"] = evt.get("progress_percent", 0.0)
        elif evt.get("kind") == "node_start":
            live_state["current_node"] = evt.get("node", "")
        elif evt.get("kind") == "node_end":
            live_state.setdefault("execution_times", {})[evt.get("node", "")] = evt.get("duration", 0)
            if evt.get("status") == "completed":
                live_state.setdefault("completed_nodes", []).append(evt.get("node", ""))
        elif evt.get("kind") == "partial_result":
            live_state.setdefault("aggregated_results", {}).setdefault("rows", []).append(
                {
                    "url": evt.get("url", ""),
                    "source_agents": evt.get("agent", ""),
                    **(evt.get("fields", {}) or {}),
                    "confidence_score": evt.get("confidence_score", 0.0),
                }
            )
        elif evt.get("kind") == "supervisor_thought":
            live_state.setdefault("supervisor_thoughts", []).append(evt.get("message", ""))

    def _on_event(evt: dict) -> None:
        live_logs.append(_format_event_line(evt))
        _merge_event_into_state(evt)
        _render_state(deepcopy(live_state), catalog=catalog, live_logs=live_logs, placeholders=placeholders)

    final_state = run_workflow(query, on_event=_on_event, enable_compare=enable_compare)
    st.session_state["last_state"] = final_state.to_dict()
    st.toast("Workflow completed")


state = st.session_state.get("last_state")
if state:
    _render_state(state, catalog=catalog, live_logs=state.get("logs"), placeholders=placeholders)

    st.divider()
    tabs = st.tabs(
        [
            "Results",
            "Presentation",
            "Compare Mode",
            "Workflow Health",
            "Langfuse",
            "Agent Performance",
            "Supervisor Analytics",
            "Workflow History",
            "Analytics",
            "Dependency Graph",
            "YAML Editor",
            "SKILL.md",
            "Replay",
            "Raw State",
            "Architecture",
        ]
    )
    with tabs[0]:
        _render_results_table(state)
    with tabs[1]:
        render_presentation_dashboard(state)
    with tabs[2]:
        _render_compare(state)
    with tabs[3]:
        render_workflow_health(state)
    with tabs[4]:
        render_langfuse_dashboard()
    with tabs[5]:
        render_agent_performance()
    with tabs[6]:
        render_supervisor_analytics()
    with tabs[7]:
        render_workflow_history(
            on_replay=lambda run_id: st.session_state.update(
                {"last_state": replay_trace(str(run_id), source="database")}
            )
        )
    with tabs[8]:
        render_analytics_dashboard()
        st.divider()
        render_metrics_dashboard()
    with tabs[9]:
        render_dependency_graph(state)
    with tabs[10]:
        render_yaml_editor()
    with tabs[11]:
        render_skill_markdown_viewer(state)
    with tabs[12]:
        frames = state.get("replay_frames") or []
        if not frames:
            st.info("No replay frames recorded.")
        else:
            idx = st.slider("Replay Frame", 0, len(frames) - 1, 0)
            st.json(frames[idx], expanded=False)
            st.progress(min(100, int(frames[idx].get("progress_percent", 0))))
    with tabs[13]:
        st.code(json.dumps(state, indent=2, default=str), language="json")
    with tabs[14]:
        render_architecture_diagram()
else:
    _render_state(
        {
            "workflow_status": "idle",
            "progress_message": "Waiting for input",
            "progress_percent": 0.0,
            "logs": ["(no run yet)"],
            "selected_skills": [],
            "skipped_skills": [],
            "execution_plan": [],
        },
        catalog=catalog,
        live_logs=["(no run yet)"],
        placeholders=placeholders,
    )
