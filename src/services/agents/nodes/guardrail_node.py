import logging
import re
import time
from typing import Dict, Literal

from ..runtime_compat import Runtime
from ..context import Context
from ..context_holder import get_current_context
from ..models import GuardrailScoring
from ..prompts import GUARDRAIL_PROMPT
from ..state import AgentState
from .utils import get_latest_query

logger = logging.getLogger(__name__)

# ── Regex fast-path ────────────────────────────────────────────────────────────
# If the query matches any of these patterns we immediately score 100 with no LLM call.
# Covers the most common cases users will type (CVE IDs, GHSA IDs, ecosystem names,
# vulnerability keywords).  Anything not matched falls through to the LLM.

_CVE_RE = re.compile(r'\bCVE-\d{4}-\d+\b', re.IGNORECASE)
_GHSA_RE = re.compile(r'\bGHSA-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}\b', re.IGNORECASE)

_SECURITY_KEYWORDS = re.compile(
    r'\b('
    r'vulnerability|vulnerabilities|advisory|advisories|exploit|malware|patch|'
    r'security\s+advisory|security\s+issue|security\s+flaw|security\s+bug|'
    r'npm|pypi|pip|node\.?js|python|rust|golang|maven|rubygems|composer|nuget|'
    r'remote\s+code\s+exec(?:ution)?|rce|sql\s+injection|xss|csrf|xxe|'
    r'affected\s+version|cvss|severity|critical|high\s+severity|'
    r'package\s+security|open\s+source\s+security|supply\s+chain'
    r')\b',
    re.IGNORECASE,
)


def _fast_path_score(query: str) -> int | None:
    """Return score=100 if query obviously belongs to the security domain, else None.

    Returns None to signal the LLM guardrail should run.
    """
    if _CVE_RE.search(query):
        return 100
    if _GHSA_RE.search(query):
        return 100
    if _SECURITY_KEYWORDS.search(query):
        return 90
    return None


def _parse_guardrail_text(text: str) -> GuardrailScoring:
    """Parse a plain-text guardrail response into GuardrailScoring.

    The prompt asks for JSON, but we also handle plain-text fallbacks so that
    even if llama3.2:1b doesn't emit valid JSON we still get a usable score.
    """
    import json

    # 1. Try JSON parse (happy path — prompt asks for JSON)
    try:
        # Strip markdown code fences if present
        clean = re.sub(r'```(?:json)?', '', text).strip().strip('`')
        data = json.loads(clean)
        score = int(data.get('score', 50))
        reason = str(data.get('reason', ''))
        return GuardrailScoring(score=max(0, min(100, score)), reason=reason)
    except Exception:
        pass

    # 2. Regex: look for a bare integer anywhere in the text
    m = re.search(r'\b(\d{1,3})\b', text)
    if m:
        score = int(m.group(1))
        if 0 <= score <= 100:
            return GuardrailScoring(score=score, reason=text[:120])

    # 3. Keyword fallback
    lower = text.lower()
    if any(w in lower for w in ('yes', 'relevant', 'security', 'advisory', 'cve')):
        return GuardrailScoring(score=75, reason='Keyword match fallback')

    return GuardrailScoring(score=50, reason='Could not parse LLM response')


def continue_after_guardrail(state: AgentState, runtime: Runtime[Context]) -> Literal["continue", "out_of_scope"]:
    """Determine whether to continue or reject based on guardrail results."""
    guardrail_result = state.get("guardrail_result")
    if not guardrail_result:
        logger.warning("No guardrail result found, defaulting to continue")
        return "continue"

    score = guardrail_result.score
    threshold = runtime.context.guardrail_threshold
    logger.info(f"Guardrail score: {score}, threshold: {threshold}")
    return "continue" if score >= threshold else "out_of_scope"


async def ainvoke_guardrail_step(
    state: AgentState,
    runtime: Runtime[Context],
) -> Dict[str, GuardrailScoring]:
    """Asynchronously invoke the guardrail validation step.

    Fast-path: CVE/GHSA/ecosystem keywords → score=100, no LLM.
    Scoped queries (file_ids/advisory_ids) → score=100, no LLM.
    Everything else → plain-text LLM call, parsed manually (no structured output overhead).
    """
    logger.info("NODE: guardrail_validation")
    start_time = time.time()

    query = get_latest_query(state["messages"])
    logger.debug(f"Evaluating query: {query[:100]}...")

    # Create span
    span = None
    if runtime.context.langfuse_enabled and runtime.context.trace:
        try:
            span = runtime.context.langfuse_tracer.create_span(
                trace=runtime.context.trace,
                name="guardrail_validation",
                input_data={"query": query, "threshold": runtime.context.guardrail_threshold},
                metadata={"node": "guardrail", "model": runtime.context.model_name},
            )
        except Exception as e:
            logger.warning(f"Failed to create span for guardrail: {e}")

    try:
        file_ids = runtime.context.file_ids
        advisory_ids = runtime.context.advisory_ids

        # ── Fast-path 1: scoped queries always pass ────────────────────────────
        if file_ids or advisory_ids:
            scope_desc = (
                f"{len(advisory_ids)} advisory/advisories" if advisory_ids
                else f"{len(file_ids)} files"
            )
            logger.info(f"Query targets {scope_desc} — guardrail bypassed (scoped), score=100")
            response = GuardrailScoring(score=100, reason="Scoped advisory/document query — guardrail bypassed")

        # ── Fast-path 2: regex keyword match — zero LLM cost ─────────────────
        elif (fast_score := _fast_path_score(query)) is not None:
            logger.info(f"Guardrail fast-path matched — score={fast_score} (no LLM call)")
            response = GuardrailScoring(
                score=fast_score,
                reason="Fast-path: security keyword/CVE/GHSA pattern detected in query",
            )

        # ── Slow-path: plain-text LLM call ────────────────────────────────────
        else:
            guardrail_prompt = GUARDRAIL_PROMPT.format(question=query)

            # Plain ainvoke — no with_structured_output, 3-5x faster on 1b models
            llm = runtime.context.ollama_client.get_langchain_model(
                model=runtime.context.model_name,
                temperature=0.0,
            )

            logger.info("Invoking LLM for guardrail (plain text, no structured output)")
            raw = await llm.ainvoke(guardrail_prompt)
            raw_text = raw.content if hasattr(raw, 'content') else str(raw)
            response = _parse_guardrail_text(raw_text)
            logger.info(f"Guardrail result — Score: {response.score}, Reason: {response.reason[:80]}")

        # Update span
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.end_span(
                span,
                output={
                    "score": response.score,
                    "reason": response.reason,
                    "decision": "continue" if response.score >= runtime.context.guardrail_threshold else "out_of_scope",
                },
                metadata={"execution_time_ms": execution_time, "threshold": runtime.context.guardrail_threshold},
            )

    except Exception as e:
        logger.error(f"Guardrail validation failed: {e}, using fallback")
        fallback_score = 80 if (file_ids or advisory_ids) else 50
        response = GuardrailScoring(
            score=fallback_score,
            reason=f"Validation failed, using {'permissive' if (file_ids or advisory_ids) else 'conservative'} default: {e}",
        )
        if span:
            execution_time = (time.time() - start_time) * 1000
            runtime.context.langfuse_tracer.update_span(
                span,
                output={"score": response.score, "reason": response.reason, "error": str(e)},
                metadata={"execution_time_ms": execution_time, "fallback": True},
                level="WARNING",
            )
            runtime.context.langfuse_tracer.end_span(span)

    return {"guardrail_result": response}
