"""
SQL Execution Sandbox
Executes the validated SQL against the PostgreSQL database.
Read-only: only SELECT statements reach this point (validator blocks anything else).
"""

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.config import DATABASE_URL
from app.state import GraphState

engine = create_engine(DATABASE_URL)


def run_sql_executor(state: GraphState) -> GraphState:
    sql = state.get("sql_query", "")

    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchall()]

        return {
            **state,
            "query_result": rows,
            "current_node": "sql_executor",
        }

    except SQLAlchemyError as e:
        return {
            **state,
            "query_result": None,
            "error_message": f"Database execution error: {str(e)}",
            "current_node": "sql_executor",
        }
