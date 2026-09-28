"""
Explanation Agent
Takes the raw query results and explains them to the user in plain English.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState
import json

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

SYSTEM_PROMPT = """You are a friendly data analyst explaining database query results to a non-technical user.

Given the user's original question and the query results, write a clear and concise explanation.

Rules:
- Use plain English, no technical jargon.
- Highlight the key insights from the data.
- If results are empty, say so clearly and suggest why.
- Keep it to 2-4 sentences unless the data warrants more detail.
- Do NOT mention SQL, databases, tables, or queries."""


def run_explanation_agent(state: GraphState) -> GraphState:
    question = state["question"]
    rows = state.get("query_result", [])
    history = state.get("clarification_history", [])

    # Build effective question from clarification history
    effective_q = question
    if history:
        effective_q += " " + " ".join(t["user_answer"] for t in history)

    # Summarize result (limit to first 20 rows for prompt size)
    result_preview = rows[:20] if rows else []
    result_str = json.dumps(result_preview, indent=2, default=str)
    total_rows = len(rows) if rows else 0

    context = (
        f"User question: {effective_q}\n\n"
        f"Result ({total_rows} row(s) total, showing up to 20):\n{result_str}"
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    explanation = llm.invoke(messages).content.strip()

    return {
        **state,
        "final_answer": explanation,
        "current_node": "explanation_agent",
    }
