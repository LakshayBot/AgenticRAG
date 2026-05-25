import logging
import time
from typing import Dict, Union

from langchain_core.messages import AIMessage
from ..runtime_compat import Runtime

from ..context import Context
from ..state import AgentState
from .utils import get_latest_query

logger = logging.getLogger(__name__)


async def ainvoke_retrieve_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, Union[int, str, list]]:
    """Initiate retrieval or return fallback if max attempts reached.

    This node creates a tool call to retrieve documents, or returns a fallback
    message if the maximum number of retrieval attempts has been reached.

    :param state: Current agent state
    :param runtime: Runtime context containing max_retrieval_attempts
    :returns: Dictionary with updated state (retrieval_attempts, messages, original_query)
    """
    logger.info("NODE: retrieve")
    start_time = time.time()

    messages = state["messages"]
    question = get_latest_query(messages)
    current_attempts = state.get("retrieval_attempts", 0)

    # Get max attempts from context
    max_attempts = runtime.context.max_retrieval_attempts

    # Store original query if not set
    updates = {}
    if state.get("original_query") is None:
        updates["original_query"] = question
        logger.debug(f"Stored original query: {question[:100]}...")

    # Create span for retrieval initiation
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="document_retrieval_initiation",
                input_data={
                    "query": question,
                    "attempt": current_attempts + 1,
                    "max_attempts": max_attempts,
                },
                metadata={
                    "node": "retrieve",
                    "top_k": runtime.context.top_k,
                },
            )
            logger.debug(f"Created Langfuse span for retrieval attempt {current_attempts + 1}")
        except Exception as e:
            logger.warning(f"Failed to create span for retrieve node: {e}")

    # Check if max attempts reached
    if current_attempts >= max_attempts:
        logger.warning(f"Max retrieval attempts ({max_attempts}) reached")
        file_ids = runtime.context.file_ids
        advisory_ids = runtime.context.advisory_ids if hasattr(runtime.context, "advisory_ids") else None
        if advisory_ids:
            fallback_msg = (
                f"I apologize, but I couldn't find relevant content in the advisory after {max_attempts} attempts.\n"
                "Please try rephrasing your question or ask about a different aspect of this advisory."
            )
        elif file_ids:
            fallback_msg = (
                f"I apologize, but I couldn't find relevant content in the uploaded document after {max_attempts} attempts.\n"
                "This may be because:\n"
                "1. The document does not contain information related to your question\n"
                "2. The query terms don't match the indexed content\n\n"
                "Please try rephrasing your question or ask about a different topic covered in the document."
            )
        else:
            fallback_msg = (
                f"I couldn't find relevant security advisories after {max_attempts} attempts.\n"
                "This may be because:\n"
                "1. No advisories in the database match your query\n"
                "2. The query terms don't match the indexed content\n\n"
                "Please try rephrasing your question using specific CVE IDs, package names, or GHSA identifiers."
            )

        # Update span with max attempts reached
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={"status": "max_attempts_reached", "fallback": True},
                metadata={"execution_time_ms": execution_time},
            )

        return {**updates, "messages": [AIMessage(content=fallback_msg)]}

    # Increment retrieval attempts
    new_attempt_count = current_attempts + 1
    updates["retrieval_attempts"] = new_attempt_count
    logger.info(f"Retrieval attempt {new_attempt_count}/{max_attempts}")

    # Get file_ids and advisory_ids from context for filtering
    file_ids = runtime.context.file_ids
    advisory_ids = runtime.context.advisory_ids if hasattr(runtime.context, "advisory_ids") else None
    if file_ids:
        logger.info(f"Filtering retrieval by file_ids: {file_ids}")
    if advisory_ids:
        logger.info(f"Filtering retrieval by advisory_ids: {advisory_ids}")

    # Create tool call for retrieval with optional file/advisory filtering
    tool_args = {"query": question}
    if file_ids:
        tool_args["file_ids"] = file_ids
    if advisory_ids:
        tool_args["advisory_ids"] = advisory_ids

    updates["messages"] = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": f"retrieve_{new_attempt_count}",
                    "name": "retrieve_papers",
                    "args": tool_args,
                }
            ],
        )
    ]

    logger.debug(f"Created tool call for query: {question[:100]}...")

    # Update span with successful tool call creation
    if span:
        execution_time = (time.time() - start_time) * 1000
        runtime.context.langfuse_tracer.end_span(
            span,
            output={
                "status": "tool_call_created",
                "query": question,
                "attempt": new_attempt_count,
            },
            metadata={"execution_time_ms": execution_time},
        )

    return updates
