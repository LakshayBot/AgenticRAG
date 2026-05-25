import logging
import re
import time
from typing import Dict

from ..runtime_compat import Runtime

from ..context import Context
from ..models import GradeDocuments, GradingResult
from ..prompts import GRADE_DOCUMENTS_PROMPT
from ..state import AgentState
from .utils import get_latest_context, get_latest_query, extract_sources_from_tool_messages

logger = logging.getLogger(__name__)


def _parse_grade_text(text: str) -> GradeDocuments:
    """Parse a plain-text grading response into GradeDocuments.

    The prompt asks for JSON with 'binary_score' and 'reasoning', but we also
    handle plain-text fallbacks so llama3.2:1b quirks don't break grading.
    """
    import json

    # 1. Try JSON parse
    try:
        clean = re.sub(r'```(?:json)?', '', text).strip().strip('`')
        data = json.loads(clean)
        score = str(data.get('binary_score', '')).lower().strip()
        reasoning = str(data.get('reasoning', text[:120]))
        binary = 'yes' if score in ('yes', '1', 'true', 'relevant') else 'no'
        return GradeDocuments(binary_score=binary, reasoning=reasoning)
    except Exception:
        pass

    # 2. Keyword scan on raw text
    lower = text.lower()
    if re.search(r'\byes\b|\brelevant\b|\brelated\b', lower):
        return GradeDocuments(binary_score='yes', reasoning=text[:120])
    if re.search(r'\bno\b|\bnot relevant\b|\birrelevant\b|\bunrelated\b', lower):
        return GradeDocuments(binary_score='no', reasoning=text[:120])

    # 3. Conservative default — assume relevant so we don't pointlessly rewrite
    return GradeDocuments(binary_score='yes', reasoning='Could not parse LLM response — defaulting to relevant')


async def ainvoke_grade_documents_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, str | list]:
    """Grade retrieved documents for relevance using LLM.

    Uses plain-text LLM inference + manual parse instead of with_structured_output
    to avoid the 3-5x latency overhead of forced JSON schema generation on small models.

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with routing_decision and grading_results
    """
    logger.info("NODE: grade_documents")
    start_time = time.time()

    # Skip grading for uploaded documents or advisory queries - trust the search results
    file_ids = runtime.context.file_ids if hasattr(runtime.context, "file_ids") else None
    advisory_ids = runtime.context.advisory_ids if hasattr(runtime.context, "advisory_ids") else None
    if file_ids or advisory_ids:
        scope_desc = f"advisory ({advisory_ids})" if advisory_ids else f"uploaded documents ({len(file_ids)} files)"
        logger.info(f"Scoped query detected ({scope_desc}) - skipping LLM grading, auto-approving search results")
        relevant_sources = extract_sources_from_tool_messages(state["messages"])
        logger.info(f"Extracted {len(relevant_sources)} sources from tool messages")
        return {
            "routing_decision": "generate_answer",
            "relevant_sources": relevant_sources,
            "grading_results": [
                GradingResult(
                    document_id="scoped_document",
                    is_relevant=True,
                    score=1.0,
                    reasoning="Scoped query (advisory or uploaded document) — auto-approved",
                )
            ],
        }

    # Get query and context
    question = get_latest_query(state["messages"])
    context = get_latest_context(state["messages"])

    chunks_preview = []
    if context:
        context_preview = context[:500] + "..." if len(context) > 500 else context
        chunks_preview = [{"text_preview": context_preview, "length": len(context)}]

    # Create span
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="document_grading",
                input_data={
                    "query": question,
                    "context_length": len(context) if context else 0,
                    "has_context": context is not None,
                    "chunks_received": chunks_preview,
                },
                metadata={"node": "grade_documents", "model": runtime.context.model_name},
            )
        except Exception as e:
            logger.warning(f"Failed to create span for grade_documents node: {e}")

    if not context:
        logger.warning("No context found, routing to rewrite_query")
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={"routing_decision": "rewrite_query", "reason": "no_context"},
                metadata={"execution_time_ms": execution_time},
            )
        return {"routing_decision": "rewrite_query", "grading_results": []}

    logger.debug(f"Grading context of length {len(context)} characters")

    try:
        grading_prompt = GRADE_DOCUMENTS_PROMPT.format(context=context, question=question)

        # Plain ainvoke — no with_structured_output schema overhead
        llm = runtime.context.ollama_client.get_langchain_model(
            model=runtime.context.model_name,
            temperature=0.0,
        )

        logger.info("Invoking LLM for document grading (plain text, no structured output)")
        raw = await llm.ainvoke(grading_prompt)
        raw_text = raw.content if hasattr(raw, 'content') else str(raw)
        grading_response = _parse_grade_text(raw_text)

        is_relevant = grading_response.binary_score == "yes"
        score = 1.0 if is_relevant else 0.0

        logger.info(f"LLM grading: score={grading_response.binary_score}, reasoning={grading_response.reasoning[:80]}")

        grading_result = GradingResult(
            document_id="retrieved_docs",
            is_relevant=is_relevant,
            score=score,
            reasoning=grading_response.reasoning,
        )

    except Exception as e:
        logger.error(f"LLM grading failed: {e}, falling back to heuristic")
        is_relevant = len(context.strip()) > 50
        score = 1.0 if is_relevant else 0.0
        grading_result = GradingResult(
            document_id="retrieved_docs",
            is_relevant=is_relevant,
            score=score,
            reasoning=f"Fallback heuristic (LLM failed): {'sufficient content' if is_relevant else 'insufficient content'}",
        )

    route = "generate_answer" if is_relevant else "rewrite_query"
    logger.info(f"Grading result: {'relevant' if is_relevant else 'not relevant'}, routing to: {route}")

    if span:
        execution_time = (time.time() - start_time) * 1000
        runtime.context.langfuse_tracer.end_span(
            span,
            output={
                "routing_decision": route,
                "is_relevant": is_relevant,
                "score": score,
                "reasoning": grading_result.reasoning,
            },
            metadata={"execution_time_ms": execution_time, "context_length": len(context)},
        )

    return {
        "routing_decision": route,
        "grading_results": [grading_result],
    }
