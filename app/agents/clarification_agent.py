"""
Clarification Agent
Generates a minimal clarifying question when the intent agent finds the question ambiguous.
In simulation mode (current), it auto-generates both the question AND a simulated user answer.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

CLARIFICATION_SYSTEM = """You are a clarification agent for a Text-to-SQL system working with an e-commerce database.

The database has:
- customers, categories, products, orders, order_items

Your job: given an ambiguous user question (and any prior clarification history), ask ONE short clarifying question that would resolve the most critical ambiguity so SQL can be generated.

Respond with ONLY the clarifying question. No explanations. No options list. Just the question."""

SIMULATION_SYSTEM = """You are simulating a user responding to a clarifying question about an e-commerce database query.
Given the original question and the clarifying question asked, respond with a brief, realistic user answer (1-2 sentences max).
If the original question is intentionally vague and the user seems uncooperative, give an unclear or unhelpful answer."""

def run_clarification_agent(state: GraphState) -> GraphState:
    question = state["question"]
    history = state.get("clarification_history", [])

    # Build context
    context = f"User question: {question}"
    if history:
        context += "\n\nPrevious clarification rounds:"
        for turn in history:
            context += f"\n- Agent asked: {turn['agent_question']}"
            context += f"\n- User answered: {turn['user_answer']}"

    # Generate clarifying question
    messages = [
        SystemMessage(content=CLARIFICATION_SYSTEM),
        HumanMessage(content=context),
    ]
    clarifying_q = llm.invoke(messages).content.strip()

    return {
        **state,
        "pending_clarification": clarifying_q,
        "clarification_retries": state.get("clarification_retries", 0) + 1,
        "current_node": "clarification_agent",
    }

