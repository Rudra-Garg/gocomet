from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

from backend.agents.extractor import extract_document
from backend.agents.router import decide_route
from backend.agents.validator import validate_extraction
from backend.config import Settings
from backend.pipeline.state import PipelineState
from backend.storage.db import load_ruleset, save_pipeline_run


def build_graph(settings: Settings):
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise RuntimeError(
            "langgraph and langgraph-checkpoint-sqlite are required.",
        ) from exc

    workflow = StateGraph(PipelineState)
    workflow.add_node("extract", _guarded(lambda state: _extract(state, settings)))
    workflow.add_node("validate", _guarded(lambda state: _validate(state, settings)))
    workflow.add_node("route", _guarded(lambda state: _route(state, settings)))
    workflow.add_node("store", _guarded(lambda state: _store(state, settings)))

    workflow.set_entry_point("extract")
    workflow.add_conditional_edges(
        "extract",
        _continue_or_end,
        {"continue": "validate", "end": END},
    )
    workflow.add_conditional_edges(
        "validate",
        _continue_or_end,
        {"continue": "route", "end": END},
    )
    workflow.add_conditional_edges(
        "route",
        _continue_or_end,
        {"continue": "store", "end": END},
    )
    workflow.add_edge("store", END)

    checkpoint_connection = sqlite3.connect(
        settings.checkpoint_db_path,
        check_same_thread=False,
    )
    checkpointer = SqliteSaver(checkpoint_connection)
    return workflow.compile(checkpointer=checkpointer)


def run_pipeline(state: PipelineState, settings: Settings) -> PipelineState:
    graph = build_graph(settings)
    return graph.invoke(
        state,
        config={"configurable": {"thread_id": state["run_id"]}},
    )


def _guarded(
    fn: Callable[[PipelineState], dict[str, Any]],
) -> Callable[[PipelineState], dict[str, Any]]:
    def wrapped(state: PipelineState) -> dict[str, Any]:
        if state.get("error"):
            return {}
        try:
            return fn(state)
        except Exception as exc:
            return {"error": str(exc)}

    return wrapped


def _extract(state: PipelineState, settings: Settings) -> dict[str, Any]:
    return {
        "extraction": extract_document(
            run_id=state["run_id"],
            document_bytes=state["document_bytes"],
            document_mime=state["document_mime"],
            settings=settings,
        ),
    }


def _validate(state: PipelineState, settings: Settings) -> dict[str, Any]:
    extraction = state.get("extraction")
    if extraction is None:
        raise ValueError("Pipeline state is missing extraction output")
    ruleset = load_ruleset(state["customer_id"])
    return {"validation": validate_extraction(extraction, ruleset)}


def _route(state: PipelineState, settings: Settings) -> dict[str, Any]:
    validation = state.get("validation")
    if validation is None:
        raise ValueError("Pipeline state is missing validation output")
    return {"decision": decide_route(validation, settings)}


def _store(state: PipelineState, settings: Settings) -> dict[str, Any]:
    save_pipeline_run(state, settings.db_path)
    return {}


def _continue_or_end(state: PipelineState) -> str:
    return "end" if state.get("error") else "continue"
