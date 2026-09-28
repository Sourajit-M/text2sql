"""
SQL Validator Agent
Checks generated SQL for:
  - Unsafe operations (DROP, DELETE, UPDATE, etc.)
  - Non-existent tables or columns
  - Incorrect JOINs
  - Intent alignment with user question
  - Excessively expensive patterns (CROSS JOIN, missing WHERE on large tables)

On issues: attempts self-correction and flags for retry.
On pass: marks valid and proceeds to execution.
"""

import re
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import GROQ_API_KEY, GROQ_MODEL
from app.state import GraphState

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0)

# Tables that actually exist
VALID_TABLES = {"customers", "categories", "products", "orders", "order_items"}

# Dangerous SQL keywords (case-insensitive)
DANGEROUS_PATTERN = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)

VALIDATION_SYSTEM = """You are a SQL validator and self-corrector for a PostgreSQL e-commerce database.

Database schema:
- customers (customer_id, name, email, city, created_at)
- categories (category_id, name)
- products (product_id, name, category_id, price, stock)
- orders (order_id, customer_id, status, ordered_at)
- order_items (item_id, order_id, product_id, quantity, unit_price)

Relationships:
- customers.customer_id = orders.customer_id
- orders.order_id = order_items.order_id
- products.product_id = order_items.product_id
- categories.category_id = products.category_id

Your task:
1. Check if the SQL query is syntactically correct PostgreSQL.
2. Verify all referenced tables and columns exist.
3. Verify JOIN conditions are correct.
4. Check if the query matches the user's intent.
5. Flag any CROSS JOINs or full table scans without WHERE on large result sets.

Respond in this EXACT format:
VALID: YES or NO
ISSUES: <comma-separated list of issues, or NONE>
CORRECTED_SQL: <corrected SQL if there are fixable issues, else NONE>"""


def _has_dangerous_ops(sql: str) -> list[str]:
    matches = DANGEROUS_PATTERN.findall(sql)
    return list(set(m.upper() for m in matches))


def _referenced_tables(sql: str) -> set[str]:
    """Very simple extraction of table names from SQL."""
    # Look for FROM and JOIN clauses
    pattern = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)
    return {m.group(1).lower() for m in pattern.finditer(sql)}


def run_sql_validator(state: GraphState) -> GraphState:
    sql = state.get("sql_query", "")
    question = state["question"]
    history = state.get("clarification_history", [])
    retries = state.get("validation_retries", 0)

    issues: list[str] = []

    # 1. Hard check: dangerous operations
    dangerous = _has_dangerous_ops(sql)
    if dangerous:
        return {
            **state,
            "validation_result": {
                "valid": False,
                "issues": [f"Unsafe SQL operation(s) detected: {', '.join(dangerous)}"],
                "corrected_sql": None,
            },
            "error_message": f"Refused to execute: SQL contains unsafe operation(s): {', '.join(dangerous)}",
            "current_node": "sql_validator",
        }

    # 2. Hard check: unknown tables
    ref_tables = _referenced_tables(sql)
    unknown = ref_tables - VALID_TABLES
    if unknown:
        issues.append(f"Unknown table(s): {', '.join(unknown)}")

    # 3. LLM-based validation (syntax, joins, intent, cost)
    context = (
        f"User question: {question}\n"
        + (
            "\nClarification context:\n"
            + "\n".join(f"  Q: {t['agent_question']}\n  A: {t['user_answer']}" for t in history)
            if history
            else ""
        )
        + f"\n\nSQL to validate:\n{sql}"
    )

    messages = [
        SystemMessage(content=VALIDATION_SYSTEM),
        HumanMessage(content=context),
    ]
    response = llm.invoke(messages).content.strip()

    # Parse LLM response
    llm_valid = True
    llm_issues: list[str] = []
    corrected_sql = None

    for line in response.splitlines():
        if line.startswith("VALID:"):
            llm_valid = line.split(":", 1)[1].strip().upper() == "YES"
        elif line.startswith("ISSUES:"):
            raw = line.split(":", 1)[1].strip()
            if raw.upper() != "NONE":
                llm_issues = [i.strip() for i in raw.split(",")]
        elif line.startswith("CORRECTED_SQL:"):
            raw = line.split(":", 1)[1].strip()
            if raw.upper() != "NONE":
                corrected_sql = raw

    all_issues = issues + llm_issues
    is_valid = llm_valid and not issues

    return {
        **state,
        "validation_result": {
            "valid": is_valid,
            "issues": all_issues,
            "corrected_sql": corrected_sql,
        },
        "validation_retries": retries + 1,
        "current_node": "sql_validator",
    }
