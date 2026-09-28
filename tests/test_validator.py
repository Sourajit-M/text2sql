"""
Tests for the SQL Validator Agent (TC7–TC16).
Uses mocks so no live DB or LLM calls are needed.
"""

import pytest
from unittest.mock import patch, MagicMock
from tests.conftest import make_state
from app.agents.sql_validator import run_sql_validator, _has_dangerous_ops, _referenced_tables


# ── Unit tests for helper functions ───────────────────────────────────────────

def test_dangerous_ops_detects_drop():
    assert "DROP" in _has_dangerous_ops("DROP TABLE customers")

def test_dangerous_ops_detects_delete():
    assert "DELETE" in _has_dangerous_ops("DELETE FROM orders WHERE 1=1")

def test_dangerous_ops_detects_update():
    assert "UPDATE" in _has_dangerous_ops("UPDATE customers SET name='x'")

def test_dangerous_ops_clean_select():
    assert _has_dangerous_ops("SELECT * FROM customers") == []

def test_referenced_tables_simple():
    sql = "SELECT * FROM customers JOIN orders ON customers.customer_id = orders.customer_id"
    tables = _referenced_tables(sql)
    assert "customers" in tables
    assert "orders" in tables

def test_referenced_tables_unknown():
    sql = "SELECT * FROM nonexistent_table"
    tables = _referenced_tables(sql)
    assert "nonexistent_table" in tables


# ── TC11: SQL contains DROP/DELETE/UPDATE → FAIL immediately ──────────────────

def test_tc11_unsafe_sql_drop():
    """TC11: DROP statement is rejected without LLM call."""
    state = make_state(
        question="Show me customers",
        sql_query="DROP TABLE customers",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert result["error_message"] is not None
    assert "DROP" in result["error_message"]

def test_tc11_unsafe_sql_delete():
    """TC11: DELETE is rejected."""
    state = make_state(
        question="Remove all orders",
        sql_query="DELETE FROM orders",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert "DELETE" in result["error_message"]


# ── TC7: SQL uses non-existent column → self-correct ─────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc7_nonexistent_column(mock_llm):
    """TC7: Validator detects bad column and returns corrected SQL."""
    mock_response = MagicMock()
    mock_response.content = (
        "VALID: NO\n"
        "ISSUES: Column 'revenue' does not exist in order_items, use quantity * unit_price instead\n"
        "CORRECTED_SQL: SELECT p.name, SUM(oi.quantity * oi.unit_price) AS revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.name ORDER BY revenue DESC LIMIT 10"
    )
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Which products generated the most revenue?",
        sql_query="SELECT p.name, SUM(oi.revenue) FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.name",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert result["validation_result"]["corrected_sql"] is not None
    assert "unit_price" in result["validation_result"]["corrected_sql"]


# ── TC8: SQL uses non-existent table → self-correct ──────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc8_nonexistent_table(mock_llm):
    """TC8: Unknown table detected by regex, LLM provides correction."""
    mock_response = MagicMock()
    mock_response.content = (
        "VALID: NO\n"
        "ISSUES: Table 'line_items' does not exist, use order_items\n"
        "CORRECTED_SQL: SELECT * FROM order_items LIMIT 100"
    )
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Show me all order line items",
        sql_query="SELECT * FROM line_items LIMIT 100",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert any("line_items" in issue for issue in result["validation_result"]["issues"])


# ── TC9: SQL has incorrect JOIN ───────────────────────────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc9_incorrect_join(mock_llm):
    """TC9: LLM detects wrong JOIN key and corrects it."""
    mock_response = MagicMock()
    mock_response.content = (
        "VALID: NO\n"
        "ISSUES: JOIN condition is wrong; orders.id should be orders.order_id\n"
        "CORRECTED_SQL: SELECT c.name FROM customers c JOIN orders o ON c.customer_id = o.customer_id LIMIT 100"
    )
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Show me all customers with orders",
        sql_query="SELECT c.name FROM customers c JOIN orders o ON c.customer_id = o.id LIMIT 100",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    # Corrected SQL should use the proper join key (customer_id, not orders.id)
    assert "customer_id" in result["validation_result"]["corrected_sql"]


# ── TC10: SQL valid but doesn't match user intent ─────────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc10_intent_mismatch(mock_llm):
    """TC10: SQL is syntactically valid but doesn't answer the question."""
    mock_response = MagicMock()
    mock_response.content = (
        "VALID: NO\n"
        "ISSUES: Query returns product count instead of revenue as user asked\n"
        "CORRECTED_SQL: SELECT p.name, SUM(oi.quantity * oi.unit_price) AS total_revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.name ORDER BY total_revenue DESC LIMIT 10"
    )
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Which products generated the most revenue?",
        sql_query="SELECT name, stock FROM products ORDER BY stock DESC LIMIT 10",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert "revenue" in result["validation_result"]["corrected_sql"]


# ── TC12: SQL fails twice, succeeds on 3rd attempt ───────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc12_success_on_third_attempt(mock_llm):
    """TC12: Valid SQL passes on 3rd try."""
    mock_response = MagicMock()
    mock_response.content = "VALID: YES\nISSUES: NONE\nCORRECTED_SQL: NONE"
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Which products generated the most revenue?",
        sql_query="SELECT p.name, SUM(oi.quantity * oi.unit_price) AS revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.name ORDER BY revenue DESC",
        validation_retries=2,  # Already tried twice
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is True
    assert result["validation_retries"] == 3


# ── TC16: Query is excessively expensive ─────────────────────────────────────

@patch("app.agents.sql_validator.llm")
def test_tc16_expensive_query(mock_llm):
    """TC16: CROSS JOIN flagged as too expensive."""
    mock_response = MagicMock()
    mock_response.content = (
        "VALID: NO\n"
        "ISSUES: CROSS JOIN without conditions is excessively expensive on large tables\n"
        "CORRECTED_SQL: SELECT c.name, o.order_id FROM customers c JOIN orders o ON c.customer_id = o.customer_id LIMIT 100"
    )
    mock_llm.invoke.return_value = mock_response

    state = make_state(
        question="Show me customers and their orders",
        sql_query="SELECT * FROM customers CROSS JOIN orders",
    )
    result = run_sql_validator(state)
    assert result["validation_result"]["valid"] is False
    assert any("expensive" in issue.lower() or "cross join" in issue.lower()
               for issue in result["validation_result"]["issues"])
