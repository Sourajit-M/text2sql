"""
Integration tests for the full LangGraph pipeline.
Covers TC1–TC6, TC13–TC15, TC17–TC18.
Uses mocks to avoid live LLM/DB calls.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from app.graph import build_graph, route_after_intent, route_after_validation, route_after_execution
from tests.conftest import make_state


# ── TC1: Unrelated question → END ─────────────────────────────────────────────

@patch("app.agents.intent_agent.llm")
def test_tc1_unrelated_question(mock_llm):
    """TC1: 'What is the capital of France?' → UNRELATED → end with error."""
    mock_response = MagicMock()
    mock_response.content = "UNRELATED"
    mock_llm.invoke.return_value = mock_response

    from app.agents.intent_agent import run_intent_agent
    state = make_state(question="What is the capital of France?")
    result = run_intent_agent(state)

    assert result["is_clear"] is False
    assert result["error_message"] is not None
    assert "unrelated" in result["error_message"].lower()


# ── TC2: Clear question → SUCCESS ─────────────────────────────────────────────

@patch("app.agents.intent_agent.llm")
def test_tc2_clear_question(mock_llm):
    """TC2: 'Which products generated the most revenue?' → CLEAR."""
    mock_response = MagicMock()
    mock_response.content = "CLEAR"
    mock_llm.invoke.return_value = mock_response

    from app.agents.intent_agent import run_intent_agent
    state = make_state(question="Which products generated the most revenue?")
    result = run_intent_agent(state)

    assert result["is_clear"] is True
    assert result["error_message"] is None


# ── TC3: Ambiguous → clarify → SUCCESS ────────────────────────────────────────

@patch("app.agents.intent_agent.llm")
def test_tc3_intent_after_clarification(mock_llm):
    """TC3: After user says 'Highest revenue', intent should be CLEAR."""
    mock_response = MagicMock()
    mock_response.content = "CLEAR"
    mock_llm.invoke.return_value = mock_response

    from app.agents.intent_agent import run_intent_agent
    state = make_state(
        question="Who was the best customer last month?",
        clarification_history=[
            {"agent_question": "What do you mean by 'best'?", "user_answer": "Highest revenue"}
        ],
    )
    result = run_intent_agent(state)
    assert result["is_clear"] is True


# ── TC4: Ambiguous 'last month' → clarify → SUCCESS ──────────────────────────

@patch("app.agents.intent_agent.llm")
def test_tc4_sales_clarification(mock_llm):
    """TC4: 'Show me sales for last month' → CLEAR after revenue clarification."""
    mock_response = MagicMock()
    mock_response.content = "CLEAR"
    mock_llm.invoke.return_value = mock_response

    from app.agents.intent_agent import run_intent_agent
    state = make_state(
        question="Show me sales for last month.",
        clarification_history=[
            {"agent_question": "Do you want total revenue or order count?", "user_answer": "Total revenue"}
        ],
    )
    result = run_intent_agent(state)
    assert result["is_clear"] is True


# ── TC5: Unclear answer → clarify again ───────────────────────────────────────

def test_tc5_route_unclear_triggers_clarification():
    """TC5: Question not clear, retries < max → route to clarification."""
    state = make_state(
        question="Show me the best products.",
        is_clear=False,
        clarification_retries=1,
    )
    route = route_after_intent(state)
    assert route == "clarification_agent"


# ── TC6: User refuses clarification → END ─────────────────────────────────────

def test_tc6_max_retries_reached():
    """TC6: After 3 failed clarifications, route to end."""
    state = make_state(
        question="Who are the best customers?",
        is_clear=False,
        clarification_retries=3,  # Hit the limit
    )
    route = route_after_intent(state)
    assert route == "end"


# ── TC13: SQL fails all 3 validation attempts → FAIL ─────────────────────────

def test_tc13_validation_retry_exhausted():
    """TC13: After 3 validation failures, route to end."""
    state = make_state(
        question="Which products generated the most revenue?",
        sql_query="SELECT * FROM products",
        validation_result={"valid": False, "issues": ["intent mismatch"], "corrected_sql": None},
        validation_retries=3,  # Exhausted
    )
    route = route_after_validation(state)
    assert route == "end"


# ── TC14: Valid SQL but DB execution fails ────────────────────────────────────

@patch("app.agents.sql_executor.engine")
def test_tc14_db_execution_error(mock_engine):
    """TC14: DB throws exception → error_message set, query_result = None."""
    from sqlalchemy.exc import SQLAlchemyError
    mock_engine.connect.return_value.__enter__ = MagicMock(
        side_effect=SQLAlchemyError("connection refused")
    )
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    from app.agents.sql_executor import run_sql_executor
    state = make_state(
        question="Which products generated the most revenue?",
        sql_query="SELECT p.name, SUM(oi.quantity * oi.unit_price) FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.name",
    )
    result = run_sql_executor(state)
    assert result["query_result"] is None
    assert result["error_message"] is not None


def test_tc14_route_after_execution_error():
    """TC14: Execution failure routes to end."""
    state = make_state(
        question="query",
        query_result=None,
        error_message="Database execution error: connection refused",
    )
    route = route_after_execution(state)
    assert route == "end"


# ── TC15: Valid query returns no rows ─────────────────────────────────────────

def test_tc15_empty_result_routes_to_explanation():
    """TC15: Empty result (not None) is a valid success — routes to explanation."""
    state = make_state(
        question="Which products were ordered in the year 1900?",
        query_result=[],  # Empty list, not None
    )
    route = route_after_execution(state)
    assert route == "explanation_agent"


@patch("app.agents.explanation_agent.llm")
def test_tc15_explanation_handles_empty_result(mock_llm):
    """TC15: Explanation agent gracefully handles 0 rows."""
    mock_response = MagicMock()
    mock_response.content = "No products were ordered in the year 1900. The database only contains recent orders."
    mock_llm.invoke.return_value = mock_response

    from app.agents.explanation_agent import run_explanation_agent
    state = make_state(
        question="Which products were ordered in the year 1900?",
        query_result=[],
    )
    result = run_explanation_agent(state)
    assert result["final_answer"] is not None
    assert len(result["final_answer"]) > 0


# ── TC17: Schema retrieval misses required table → refine ─────────────────────

@patch("app.agents.schema_agent.llm")
def test_tc17_schema_includes_order_items(mock_llm):
    """TC17: Schema agent must include order_items for revenue calculation."""
    mock_response = MagicMock()
    mock_response.content = (
        "Relevant Tables:\n"
        "- products: product_id, name\n"
        "- order_items: order_id, product_id, quantity, unit_price\n\n"
        "Required Joins:\n"
        "- products.product_id = order_items.product_id"
    )
    mock_llm.invoke.return_value = mock_response

    from app.agents.schema_agent import run_schema_agent
    state = make_state(question="Which products generated the most revenue?")
    result = run_schema_agent(state)

    assert "order_items" in result["schema_context"]
    assert "products" in result["schema_context"]


# ── TC18: 'Best customer' intent changes required schema ──────────────────────

@patch("app.agents.schema_agent.llm")
def test_tc18_schema_adapts_to_clarification(mock_llm):
    """TC18: After clarification (revenue), schema includes customers+orders+order_items."""
    mock_response = MagicMock()
    mock_response.content = (
        "Relevant Tables:\n"
        "- customers: customer_id, name\n"
        "- orders: order_id, customer_id, ordered_at\n"
        "- order_items: order_id, product_id, quantity, unit_price\n\n"
        "Required Joins:\n"
        "- customers.customer_id = orders.customer_id\n"
        "- orders.order_id = order_items.order_id"
    )
    mock_llm.invoke.return_value = mock_response

    from app.agents.schema_agent import run_schema_agent
    state = make_state(
        question="Who was the best customer last month?",
        clarification_history=[
            {"agent_question": "What do you mean by best?", "user_answer": "Highest revenue"}
        ],
    )
    result = run_schema_agent(state)

    schema = result["schema_context"]
    assert "customers" in schema
    assert "orders" in schema
    assert "order_items" in schema
