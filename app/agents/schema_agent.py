"""
Schema Agent
Identifies the relevant tables and columns for a given question.
Returns a concise schema context string instead of dumping the full DB schema.
"""

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

# Full schema reference given to the schema agent
FULL_SCHEMA = """
Tables and columns:

customers:
  - customer_id (PK, INT)
  - name (VARCHAR)
  - email (VARCHAR)
  - city (VARCHAR)
  - created_at (TIMESTAMP)

categories:
  - category_id (PK, INT)
  - name (VARCHAR)

products:
  - product_id (PK, INT)
  - name (VARCHAR)
  - category_id (FK -> categories.category_id)
  - price (NUMERIC)
  - stock (INT)

orders:
  - order_id (PK, INT)
  - customer_id (FK -> customers.customer_id)
  - status (VARCHAR: 'completed', 'pending', 'cancelled')
  - ordered_at (TIMESTAMP)

order_items:
  - item_id (PK, INT)
  - order_id (FK -> orders.order_id)
  - product_id (FK -> products.product_id)
  - quantity (INT)
  - unit_price (NUMERIC)

Relationships:
  - customers 1--* orders (via customer_id)
  - orders 1--* order_items (via order_id)
  - products 1--* order_items (via product_id)
  - categories 1--* products (via category_id)
"""

SYSTEM_PROMPT = f"""You are a schema selector for a Text-to-SQL system.
Given a user question (and its clarification context), identify ONLY the tables and columns needed to answer it.

{FULL_SCHEMA}

Return a concise schema context with:
1. The relevant tables and their needed columns
2. The join relationships required

Format:
Relevant Tables:
- table_name: col1, col2, ...

Required Joins:
- table_a.fk = table_b.pk

Keep it short and precise. Do NOT include irrelevant tables."""


def run_schema_agent(state: GraphState) -> GraphState:
    question = state["question"]
    history = state.get("clarification_history", [])

    context = f"User question: {question}"
    if history:
        context += "\n\nClarification context:"
        for turn in history:
            context += f"\n- Agent asked: {turn['agent_question']}"
            context += f"\n- User answered: {turn['user_answer']}"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    schema_context = llm.invoke(messages).content.strip()

    return {
        **state,
        "schema_context": schema_context,
        "current_node": "schema_agent",
    }
