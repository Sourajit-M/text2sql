"""
LangGraph Graph Definition
Wires all agents together with conditional edges and retry logic.
"""

from langgraph.graph import StateGraph, END
from app.state import GraphState
from app.agents.intent_agent import run_intent_agent
from app.agents.clarification_agent import run_clarification_agent
from app.agents.schema_agent import run_schema_agent
from app.agents.sql_generator import run_sql_generator
from app.agents.sql_validator import run_sql_validator
from app.agents.sql_executor import run_sql_executor
from app.agents.explanation_agent import run_explanation_agent
from app.config import MAX_CLARIFICATION_RETRIES, MAX_VALIDATION_RETRIES


# ── Routing functions ──────────────────────────────────────────────────────────

def route_after_intent(state: GraphState) -> str:
    """After intent check: clear → schema | unrelated → end | unclear → clarify or end."""
    if state.get("error_message"):
        return "end"
    if state.get("is_clear"):
        return "schema_agent"
    # Not clear — check retry limit
    if state.get("clarification_retries", 0) >= MAX_CLARIFICATION_RETRIES:
        return "end"
    return "clarification_agent"


def route_after_validation(state: GraphState) -> str:
    """After validation: valid → execute | invalid → retry or end."""
    validation = state.get("validation_result", {})

    # Hard fail (unsafe SQL) — error_message already set
    if state.get("error_message"):
        return "end"

    if validation.get("valid"):
        return "sql_executor"

    # Invalid: check retry budget
    if state.get("validation_retries", 0) >= MAX_VALIDATION_RETRIES:
        return "end"

    return "sql_generator"  # Retry with feedback


def route_after_execution(state: GraphState) -> str:
    """After execution: success → explain | DB error → end."""
    if state.get("error_message") or state.get("query_result") is None:
        return "end"
    return "explanation_agent"


def set_exhausted_error(state: GraphState) -> GraphState:
    """Terminal node: set a human-readable error if none exists."""
    if not state.get("error_message"):
        retries_c = state.get("clarification_retries", 0)
        retries_v = state.get("validation_retries", 0)
        if retries_c >= MAX_CLARIFICATION_RETRIES:
            msg = "Could not get enough information after multiple clarifications. Please rephrase your question."
        elif retries_v >= MAX_VALIDATION_RETRIES:
            msg = "Could not generate a valid SQL query after multiple attempts."
        else:
            msg = "An unexpected error occurred."
        return {**state, "error_message": msg}
    return state


# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    # Register nodes
    graph.add_node("intent_agent",        run_intent_agent)
    graph.add_node("clarification_agent", run_clarification_agent)
    graph.add_node("schema_agent",        run_schema_agent)
    graph.add_node("sql_generator",       run_sql_generator)
    graph.add_node("sql_validator",       run_sql_validator)
    graph.add_node("sql_executor",        run_sql_executor)
    graph.add_node("explanation_agent",   run_explanation_agent)
    graph.add_node("terminal_error",      set_exhausted_error)

    # Entry point
    graph.set_entry_point("intent_agent")

    # Edges from intent agent
    graph.add_conditional_edges(
        "intent_agent",
        route_after_intent,
        {
            "schema_agent":        "schema_agent",
            "clarification_agent": "clarification_agent",
            "end":                 "terminal_error",
        },
    )

    # Clarification yields control back to user/client for their answer
    graph.add_edge("clarification_agent", END)

    # Schema → SQL generator
    graph.add_edge("schema_agent", "sql_generator")

    # SQL generator → validator
    graph.add_edge("sql_generator", "sql_validator")

    # Validation routing (retry or execute)
    graph.add_conditional_edges(
        "sql_validator",
        route_after_validation,
        {
            "sql_executor":  "sql_executor",
            "sql_generator": "sql_generator",
            "end":           "terminal_error",
        },
    )

    # Execution routing
    graph.add_conditional_edges(
        "sql_executor",
        route_after_execution,
        {
            "explanation_agent": "explanation_agent",
            "end":               "terminal_error",
        },
    )

    # Terminal nodes
    graph.add_edge("explanation_agent", END)
    graph.add_edge("terminal_error",    END)

    return graph.compile()


# Singleton compiled graph
app_graph = build_graph()
