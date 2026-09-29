"""
FastAPI Application
Exposes the text-to-SQL LangGraph pipeline as a REST API.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.graph import app_graph
from app.state import GraphState

from fastapi.middleware.cors import CORSMiddleware

api = FastAPI(
    title="Text-to-SQL API",
    description="Multi-agent text-to-SQL system with clarification engine.",
    version="0.1.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev and easy deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ──────────────────────────────────────────────────

class ClarificationTurn(BaseModel):
    agent_question: str
    user_answer: str


class QueryRequest(BaseModel):
    question: str
    clarification_history: Optional[list[ClarificationTurn]] = None


class QueryResponse(BaseModel):
    success: bool
    needs_clarification: bool = False
    clarifying_question: Optional[str] = None
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
    incoming_history = [
        {"agent_question": turn.agent_question, "user_answer": turn.user_answer}
        for turn in (request.clarification_history or [])
    ]

    initial_state: GraphState = {
        "question": request.question,
        "clarification_history": incoming_history,
        "clarification_retries": len(incoming_history),
        "is_clear": False,
        "schema_context": None,
        "sql_query": None,
        "validation_result": None,
        "validation_retries": 0,
        "query_result": None,
        "final_answer": None,
        "error_message": None,
        "pending_clarification": None,
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

    pending = result.get("pending_clarification")
    needs_clarification = bool(pending)
    success = result.get("final_answer") is not None

    return QueryResponse(
        success=success,
        needs_clarification=needs_clarification,
        clarifying_question=pending,
        final_answer=result.get("final_answer"),
        sql_query=result.get("sql_query"),
        query_result=result.get("query_result"),
        clarification_history=history if history else None,
        error_message=result.get("error_message"),
    )


# ── Mount built frontend if available ──────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(frontend_dist):
    api.mount("/", StaticFiles(directory=frontend_dist, html=True), name="static")

