import logging
import re
import time
from typing import Dict, List

from langchain_core.messages import HumanMessage
from ..runtime_compat import Runtime
from pydantic import BaseModel, Field

from ..context import Context
from ..prompts import REWRITE_PROMPT
from ..state import AgentState

logger = logging.getLogger(__name__)


class QueryRewriteOutput(BaseModel):
    """Structured output for query rewriting."""

    rewritten_query: str = Field(description="The improved query optimized for document retrieval")
    reasoning: str = Field(description="Brief explanation of how the query was improved")


def _parse_rewrite_text(text: str, original_question: str) -> tuple[str, str]:
    """Parse a plain-text rewrite response.

    Returns (rewritten_query, reasoning).
    """
    import json

    # 1. Try JSON parse (prompt asks for JSON via structured output historically, but now plain)
    try:
        clean = re.sub(r'```(?:json)?', '', text).strip().strip('`')
        data = json.loads(clean)
        rq = str(data.get('rewritten_query', '')).strip()
        reasoning = str(data.get('reasoning', ''))
        if rq:
            return rq, reasoning
    except Exception:
        pass

    # 2. Take the first non-empty line as the rewritten query
    for line in text.splitlines():
        line = line.strip().strip('"').strip("'")
        if line and len(line) > 10:
            return line, "Plain text extraction"

    # 3. Fallback — append security keywords
    return f"{original_question} security vulnerability advisory", "Fallback keyword expansion"


async def ainvoke_rewrite_query_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, str | List]:
    """Rewrite the original query for better document retrieval using LLM.

    This node uses an LLM to intelligently rewrite the user's query
    to improve the chances of finding relevant documents.

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with rewritten_query and updated messages
    """
    logger.info("NODE: rewrite_query")
    start_time = time.time()

    # Get original query
    original_question = state.get("original_query") or state["messages"][0].content
    current_attempt = state.get("retrieval_attempts", 0)

    logger.debug(f"Rewriting query using LLM: {original_question[:100]}...")

    # Create span for query rewriting
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="query_rewriting",
                input_data={
                    "original_query": original_question,
                    "attempt": current_attempt,
                },
                metadata={
                    "node": "rewrite_query",
                    "strategy": "llm_based_expansion",
                    "model": runtime.context.model_name,
                },
            )
            logger.debug("Created Langfuse span for query rewriting")
        except Exception as e:
            logger.warning(f"Failed to create span for rewrite_query node: {e}")

    # Use LLM to rewrite the query — plain text call, no structured output overhead
    try:
        llm = runtime.context.ollama_client.get_langchain_model(
            model=runtime.context.model_name,
            temperature=0.3,
        )

        prompt = REWRITE_PROMPT.format(question=original_question)

        logger.debug(f"Invoking LLM for query rewriting (plain text, model: {runtime.context.model_name})")
        llm_start = time.time()

        raw = await llm.ainvoke(prompt)
        raw_text = raw.content if hasattr(raw, 'content') else str(raw)
        rewritten_query, reasoning = _parse_rewrite_text(raw_text, original_question)

        if not rewritten_query:
            raise ValueError("Empty rewritten query after parsing")

        llm_duration = time.time() - llm_start
        logger.info(
            f"Query rewritten in {llm_duration:.2f}s: "
            f"'{original_question[:50]}...' -> '{rewritten_query[:50]}...'"
        )

    except Exception as e:
        logger.error(f"Failed to rewrite query using LLM: {e}")
        logger.warning("Falling back to simple keyword expansion")
        # Fallback to simple expansion if LLM fails
        rewritten_query = f"{original_question} security vulnerability advisory"
        reasoning = "Fallback: Simple keyword expansion due to LLM error"

    # Update span with rewriting result
    if span:
        execution_time = (time.time() - start_time) * 1000
        runtime.context.langfuse_tracer.end_span(
            span,
            output={
                "rewritten_query": rewritten_query,
                "reasoning": reasoning,
                "original_query": original_question,
            },
            metadata={
                "execution_time_ms": execution_time,
                "original_length": len(original_question),
                "rewritten_length": len(rewritten_query),
                "llm_duration_seconds": llm_duration if "llm_duration" in locals() else None,
            },
        )

    return {
        "messages": [HumanMessage(content=rewritten_query)],
        "rewritten_query": rewritten_query,
    }
