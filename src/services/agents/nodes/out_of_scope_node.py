import logging
from typing import Dict, List

from langchain_core.messages import AIMessage
from ..runtime_compat import Runtime

from ..context import Context
from ..state import AgentState
from .utils import get_latest_query

logger = logging.getLogger(__name__)


async def ainvoke_out_of_scope_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, List[AIMessage]]:
    """Handle out-of-scope queries with a helpful message.

    When the query targets uploaded documents, the message acknowledges
    those documents. For general queries, it explains the academic scope.

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with messages containing the out-of-scope response
    """
    logger.info("NODE: out_of_scope")

    question = get_latest_query(state["messages"])
    file_ids = runtime.context.file_ids if hasattr(runtime.context, "file_ids") else None

    if file_ids:
        response_text = (
            "I wasn't able to determine how to answer your question based on the uploaded document(s).\n\n"
            f"Your question: '{question}'\n\n"
            "Please try rephrasing your question, or ask something more directly related to the content "
            "of the document you uploaded."
        )
    else:
        response_text = (
            "I apologize, but I can only help with questions about security advisories, "
            "CVEs, software vulnerabilities, and threat intelligence.\n\n"
            f"Your question: '{question}'\n\n"
            "This appears to be outside my domain of expertise. Try asking about:\n"
            "- Specific CVEs or GHSA advisories\n"
            "- Vulnerable packages or ecosystems\n"
            "- Severity levels and affected versions\n\n"
            "If you have a security-related question, I'm happy to help!"
        )

    logger.info("Responding with out-of-scope message")

    return {"messages": [AIMessage(content=response_text)]}
