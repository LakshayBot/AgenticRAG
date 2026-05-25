import logging
import re
import time
from typing import Dict, List

from langchain_core.messages import AIMessage
from ..runtime_compat import Runtime

from ..context import Context
from ..prompts import GENERATE_ANSWER_PROMPT
from ..state import AgentState
from .utils import get_latest_context, get_latest_query

logger = logging.getLogger(__name__)

# Patterns that indicate the LLM echoed raw metadata instead of synthesising prose
_RAW_METADATA_LABELS = re.compile(
    r"(Affected Package:|CVSS Score:|Severity:|GHSA-\w+-\w+-\w+\)?\s+Affected Package:)",
    re.IGNORECASE,
)


def _reformat_raw_metadata_dump(text: str) -> str:
    """Detect raw metadata echo from small models and reformat into readable prose.

    When llama3.2:1b simply repeats the context chunk instead of synthesising
    an answer, the output looks like:
        "Title (GHSA-xxxx) Affected Package: foo Severity: CRITICAL CVE: ... CVSS Score: 9.6"

    This function converts that into a readable sentence rather than showing
    the user raw field labels.
    """
    if not _RAW_METADATA_LABELS.search(text):
        return text  # looks fine, leave it alone

    # Try to extract key fields with simple regex and build a sentence
    title_m = re.match(r"^([^(]+)\(", text)
    ghsa_m = re.search(r"(GHSA-[\w-]+)", text, re.IGNORECASE)
    cve_m = re.search(r"(CVE-\d{4}-\d+)", text, re.IGNORECASE)
    pkg_m = re.search(r"Affected Package:\s*([^\s,;]+)", text, re.IGNORECASE)
    sev_m = re.search(r"Severity:\s*([A-Z]+)", text, re.IGNORECASE)
    cvss_m = re.search(r"CVSS Score:\s*([\d.]+)", text, re.IGNORECASE)

    title = title_m.group(1).strip() if title_m else None
    ghsa = ghsa_m.group(1) if ghsa_m else None
    cve = cve_m.group(1) if cve_m else None
    pkg = pkg_m.group(1) if pkg_m else None
    sev = sev_m.group(1).capitalize() if sev_m else None
    cvss = cvss_m.group(1) if cvss_m else None

    parts: list[str] = []
    if title and ghsa:
        parts.append(f"**{title}** ({ghsa}{f' / {cve}' if cve else ''}) is a {sev or 'security'}-severity vulnerability")
    elif ghsa:
        parts.append(f"**{ghsa}**{f' ({cve})' if cve else ''} is a {sev or 'security'}-severity vulnerability")
    else:
        # Can't parse well enough — return the original rather than garbling it further
        return text

    if pkg:
        parts.append(f"affecting the **{pkg}** package")
    if cvss:
        parts.append(f"with a CVSS score of **{cvss}**")

    return " ".join(parts) + "."


async def ainvoke_generate_answer_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, List[AIMessage]]:
    """Generate final answer using retrieved documents.

    This node generates a comprehensive answer to the
    user's question based on the retrieved context using an LLM.

    :param state: Current agent state
    :param runtime: Runtime context
    :returns: Dictionary with messages containing the generated answer
    """
    logger.info("NODE: generate_answer")
    start_time = time.time()

    # Get question and context
    question = get_latest_query(state["messages"])
    context = get_latest_context(state["messages"])

    # Count sources from relevant_sources
    sources_count = len(state.get("relevant_sources", []))

    if not context:
        # For scoped queries (advisory / uploaded PDF), return a clear "nothing indexed" message
        # instead of asking the LLM to answer with no context — it produces confusing output.
        file_ids = getattr(runtime.context, "file_ids", None)
        advisory_ids = getattr(runtime.context, "advisory_ids", None)
        if advisory_ids:
            answer = (
                "No content has been indexed for this advisory yet. "
                "Try syncing the advisory data first, then ask your question again."
            )
            logger.warning(f"No chunks found for advisory_ids={advisory_ids} — returning early")
            return {"messages": [AIMessage(content=answer)]}
        if file_ids:
            answer = (
                "No content could be retrieved from the uploaded document. "
                "The file may still be processing, or the document may not contain text that matches your question."
            )
            logger.warning(f"No chunks found for file_ids={file_ids} — returning early")
            return {"messages": [AIMessage(content=answer)]}
        # General (non-scoped) fallback — let the LLM handle it gracefully
        context = "No relevant documents found."
        logger.warning("No context available for answer generation")

    # Truncate context to avoid oversized prompts on small models (llama3.2:1b is slow with long input)
    MAX_CONTEXT_CHARS = 2500
    if len(context) > MAX_CONTEXT_CHARS:
        logger.info(f"Truncating context from {len(context)} to {MAX_CONTEXT_CHARS} chars for prompt efficiency")
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated for brevity]"

    logger.debug(f"Generating answer for query: {question[:100]}...")
    logger.debug(f"Using context of length: {len(context)} characters")

    # Extract document chunks preview for logging
    chunks_preview = []
    if context:
        context_preview = context[:1000] + "..." if len(context) > 1000 else context
        chunks_preview = [{"text_preview": context_preview, "length": len(context)}]

    # Create span for answer generation
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="answer_generation",
                input_data={
                    "query": question,
                    "context_length": len(context),
                    "sources_count": sources_count,
                    "chunks_used": chunks_preview,
                },
                metadata={
                    "node": "generate_answer",
                    "model": runtime.context.model_name,
                    "temperature": runtime.context.temperature,
                },
            )
            logger.debug("Created Langfuse span for answer generation")
        except Exception as e:
            logger.warning(f"Failed to create span for generate_answer node: {e}")

    try:
        # Create answer generation prompt from template
        answer_prompt = GENERATE_ANSWER_PROMPT.format(
            context=context,
            question=question,
        )

        # Get LLM from runtime context
        llm = runtime.context.ollama_client.get_langchain_model(
            model=runtime.context.model_name,
            temperature=runtime.context.temperature,
        )

        # Invoke LLM for answer generation
        logger.info("Invoking LLM for answer generation")
        response = await llm.ainvoke(answer_prompt)

        # Extract content from response
        answer = response.content if hasattr(response, "content") else str(response)
        answer = _reformat_raw_metadata_dump(answer)
        logger.info(f"Generated answer of length: {len(answer)} characters")

        # Update span with successful result
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={
                    "answer_length": len(answer),
                    "sources_used": sources_count,
                },
                metadata={
                    "execution_time_ms": execution_time,
                    "context_length": len(context),
                },
            )

    except Exception as e:
        logger.error(f"LLM answer generation failed: {e}, falling back to error message")

        # Fallback to error message if LLM fails
        answer = f"I apologize, but I encountered an error while generating the answer: {str(e)}\n\nPlease try again or rephrase your question."

        # Update span with error
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.update_span(
                span,
                output={"error": str(e), "fallback": True},
                metadata={"execution_time_ms": execution_time},
                level="ERROR",
            )
            runtime.context.langfuse_tracer.end_span(span)

    return {"messages": [AIMessage(content=answer)]}
