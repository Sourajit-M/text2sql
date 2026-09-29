from typing import Annotated, Optional
from typing_extensions import TypedDict
import operator


class GraphState(TypedDict):
    # The original user question
    question: str

    # Accumulated clarification Q&A turns
    clarification_history: list[dict]  # [{"agent_question": ..., "user_answer": ...}]

    # Number of clarification attempts so far
    clarification_retries: int

    # Whether the question is clear enough to proceed
    is_clear: bool

    # Relevant schema context retrieved by schema agent
    schema_context: Optional[str]

    # Generated SQL query
    sql_query: Optional[str]

    # Validation result from validator agent
    validation_result: Optional[dict]  # {"valid": bool, "issues": [...], "corrected_sql": ...}

    # Number of validation/self-correction attempts
    validation_retries: int

    # Raw rows returned from DB execution
    query_result: Optional[list]

    # Final natural-language explanation for the user
    final_answer: Optional[str]

    # Terminal error message (when we give up)
    error_message: Optional[str]

    # Pending question for user clarification (if agent is waiting for real user answer)
    pending_clarification: Optional[str]

    # Which node/phase we're currently in (for routing logic)
    current_node: Optional[str]
