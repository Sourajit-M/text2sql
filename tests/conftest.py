"""
Shared pytest fixtures and helpers for text2sql tests.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.state import GraphState


def make_state(**kwargs) -> GraphState:
    """Build a minimal valid GraphState with defaults."""
    defaults: GraphState = {
        "question": "test question",
        "clarification_history": [],
        "clarification_retries": 0,
        "is_clear": False,
        "schema_context": None,
        "sql_query": None,
        "validation_result": None,
        "validation_retries": 0,
        "query_result": None,
        "final_answer": None,
        "error_message": None,
        "current_node": None,
    }
    return {**defaults, **kwargs}
