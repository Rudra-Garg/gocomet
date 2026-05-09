from __future__ import annotations

import sqlite3
from datetime import datetime

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
    result = graph.invoke(
        state,
        config={"configurable": {"thread_id": state.run_id}},
    )
    if isinstance(result, PipelineState):
        return result
    return PipelineState.model_validate(result)


def _guarded(fn):
    def wrapped(state: PipelineState) -> PipelineState:
        if state.error:
            return state
        try:
            next_state = fn(state)
            next_state.updated_at = datetime.utcnow()
            return next_state
        except Exception as exc:
            state.error = str(exc)
            state.updated_at = datetime.utcnow()
            return state

    return wrapped


def _extract(state: PipelineState, settings: Settings) -> PipelineState:
    if state.document is None:
        raise ValueError("Pipeline state is missing document input")
    state.extraction = extract_document(state.document, settings)
    return state


def _validate(state: PipelineState, settings: Settings) -> PipelineState:
    if state.extraction is None:
        raise ValueError("Pipeline state is missing extraction result")
    ruleset = load_ruleset(state.customer_id)
    state.validation = validate_extraction(
        state.extraction,
        ruleset,
        settings.confidence_threshold,
    )
    return state


def _route(state: PipelineState, settings: Settings) -> PipelineState:
    if state.validation is None:
        raise ValueError("Pipeline state is missing validation result")
    state.decision = decide_route(state.validation, settings)
    return state


def _store(state: PipelineState, settings: Settings) -> PipelineState:
    save_pipeline_run(state, settings.db_path)
    return state


def _continue_or_end(state: PipelineState) -> str:
    return "end" if state.error else "continue"
