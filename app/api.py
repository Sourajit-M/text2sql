"""
FastAPI Application
Exposes the text-to-SQL LangGraph pipeline as a REST API.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.graph import app_graph
from app.state import GraphState

api = FastAPI(
    title="Text-to-SQL API",
    description="Multi-agent text-to-SQL system with clarification engine.",
    version="0.1.0",
)


# ── Request / Response models ──────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str


class ClarificationTurn(BaseModel):
    agent_question: str
    user_answer: str


class QueryResponse(BaseModel):
    success: bool
    final_answer: Optional[str] = None
    sql_query: Optional[str] = None
    query_result: Optional[list] = None
    clarification_history: Optional[list[ClarificationTurn]] = None
    error_message: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@api.get("/health")
def health():
    return {"status": "ok"}


@api.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    """
    Submit a natural language question about the e-commerce database.
    The system will clarify ambiguities, generate SQL, validate, execute,
    and return a plain-English explanation.
    """
    initial_state: GraphState = {
        "question": request.question,
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

    try:
        result: GraphState = app_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    history = [
        ClarificationTurn(**turn)
        for turn in (result.get("clarification_history") or [])
    ]

    success = result.get("final_answer") is not None

    return QueryResponse(
        success=success,
        final_answer=result.get("final_answer"),
        sql_query=result.get("sql_query"),
        query_result=result.get("query_result"),
        clarification_history=history if history else None,
        error_message=result.get("error_message"),
    )
