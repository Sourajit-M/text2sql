"""
SQL Generator Agent
Produces a PostgreSQL query from the user question + clarification context + schema context.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

SYSTEM_PROMPT = """You are a PostgreSQL SQL generator for an e-commerce database.

Rules:
1. Generate ONLY a raw SQL SELECT query — no markdown, no backticks, no explanation.
2. Only use SELECT statements. Never use INSERT, UPDATE, DELETE, DROP, TRUNCATE, or any DDL/DML.
3. Use only the tables and columns provided in the schema context.
4. Use table aliases for readability.
5. For "last month" queries: use WHERE ordered_at >= NOW() - INTERVAL '30 days'
6. Always add a LIMIT 100 unless the user asks for aggregations.
7. Use proper PostgreSQL syntax."""


def run_sql_generator(state: GraphState) -> GraphState:
    question = state["question"]
    schema_context = state.get("schema_context", "")
    history = state.get("clarification_history", [])
    validation_result = state.get("validation_result")

    # Build the full context
    context_parts = [f"User question: {question}"]

    if history:
        context_parts.append("Clarification context:")
        for turn in history:
            context_parts.append(f"  - Agent asked: {turn['agent_question']}")
            context_parts.append(f"  - User answered: {turn['user_answer']}")

    context_parts.append(f"\nRelevant Schema:\n{schema_context}")

    # If this is a retry after validation failure, include the feedback
    if validation_result and not validation_result.get("valid"):
        issues = "\n".join(validation_result.get("issues", []))
        context_parts.append(f"\nPrevious SQL had issues:\n{issues}")
        if validation_result.get("corrected_sql"):
            context_parts.append(f"\nPartially corrected SQL (fix the remaining issues):\n{validation_result['corrected_sql']}")

    prompt = "\n".join(context_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    sql_query = llm.invoke(messages).content.strip()

    # Strip any accidental markdown fences
    if sql_query.startswith("```"):
        lines = sql_query.split("\n")
        sql_query = "\n".join(
            line for line in lines if not line.startswith("```")
        ).strip()

    return {
        **state,
        "sql_query": sql_query,
        "current_node": "sql_generator",
    }
