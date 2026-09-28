"""
Intent / Ambiguity Agent
Decides if the user's question is clear enough to generate SQL.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

SYSTEM_PROMPT = """You are an intent and ambiguity checker for a Text-to-SQL system.
Your only job is to decide whether a user's question contains enough information to generate a precise SQL query against an e-commerce database.

The database has these tables:
- customers (customer_id, name, email, city, created_at)
- categories (category_id, name)
- products (product_id, name, category_id, price, stock)
- orders (order_id, customer_id, status, ordered_at)
- order_items (item_id, order_id, product_id, quantity, unit_price)

Rules:
1. If the question is NOT about the e-commerce database at all (e.g. general knowledge, geography), respond with UNRELATED.
2. If the question has ambiguous terms (e.g. "best", "top", "popular") without clarification, respond with UNCLEAR.
3. If the question is clear and specific enough to write SQL, respond with CLEAR.

Respond with ONLY one of: CLEAR | UNCLEAR | UNRELATED
Do NOT add any explanation."""

def run_intent_agent(state: GraphState) -> GraphState:
    question = state["question"]
    history = state.get("clarification_history", [])

    # Build context with clarification history if any
    context = question
    if history:
        context += "\n\nClarification history:"
        for turn in history:
            context += f"\n- Agent asked: {turn['agent_question']}"
            context += f"\n- User answered: {turn['user_answer']}"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    verdict = response.content.strip().upper()

    if verdict == "CLEAR":
        return {**state, "is_clear": True, "current_node": "intent_agent"}
    elif verdict == "UNRELATED":
        return {
            **state,
            "is_clear": False,
            "error_message": "I can only answer questions about the e-commerce database. Your question seems unrelated.",
            "current_node": "intent_agent",
        }
    else:
        return {**state, "is_clear": False, "current_node": "intent_agent"}
