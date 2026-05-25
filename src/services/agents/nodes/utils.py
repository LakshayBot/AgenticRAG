import json
import logging
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ..models import ReasoningStep, SourceItem, ToolArtefact

logger = logging.getLogger(__name__)


def _parse_tool_message_documents(content: str) -> List[Dict]:
    """Parse LangChain ToolNode document content into a list of dicts.

    LangChain's ToolNode serializes List[Document] as a JSON array of
    {"page_content": "...", "metadata": {...}} objects.

    :param content: Raw ToolMessage content string
    :returns: List of document dicts with page_content and metadata keys
    """
    if not content:
        return []
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: return raw content as a single text block
    return [{"page_content": content, "metadata": {}}]


def extract_sources_from_tool_messages(messages: List) -> List[SourceItem]:
    """Extract sources from tool messages in conversation.

    :param messages: List of messages from graph state
    :returns: List of SourceItem objects
    """
    sources = []

    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "retrieve_papers":
            docs = _parse_tool_message_documents(msg.content)
            for doc in docs:
                metadata = doc.get("metadata", {})
                source_id = metadata.get("source_id", "")
                if not source_id:
                    continue
                source = SourceItem(
                    source_id=source_id,
                    title=metadata.get("title", ""),
                    authors=metadata.get("authors", []) if isinstance(metadata.get("authors"), list) else [],
                    url=metadata.get("source", ""),
                    relevance_score=float(metadata.get("score", 0.0)),
                )
                sources.append(source)

    return sources


def extract_tool_artefacts(messages: List) -> List[ToolArtefact]:
    """Extract tool artifacts from messages.

    :param messages: List of messages from graph state
    :returns: List of ToolArtefact objects
    """
    artefacts = []

    for msg in messages:
        if isinstance(msg, ToolMessage):
            artefact = ToolArtefact(
                tool_name=getattr(msg, "name", "unknown"),
                tool_call_id=getattr(msg, "tool_call_id", ""),
                content=msg.content,
                metadata={},
            )
            artefacts.append(artefact)

    return artefacts


def create_reasoning_step(
    step_name: str,
    description: str,
    metadata: Optional[Dict] = None,
) -> ReasoningStep:
    """Create a reasoning step record.

    :param step_name: Name of the step/node
    :param description: Human-readable description
    :param metadata: Additional metadata
    :returns: ReasoningStep object
    """
    return ReasoningStep(
        step_name=step_name,
        description=description,
        metadata=metadata or {},
    )


def filter_messages(messages: List) -> List[AIMessage | HumanMessage]:
    """Filter messages to include only HumanMessage and AIMessage types.

    Excludes tool messages and other internal message types.

    :param messages: List of messages to filter
    :returns: Filtered list of messages
    """
    return [msg for msg in messages if isinstance(msg, (HumanMessage, AIMessage))]


def get_latest_query(messages: List) -> str:
    """Get the latest user query from messages.

    :param messages: List of messages
    :returns: Latest query text
    :raises ValueError: If no user query found
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content

    raise ValueError("No user query found in messages")


def get_latest_context(messages: List) -> str:
    """Get the latest context from tool messages, formatted as clean text.

    LangChain's ToolNode serializes List[Document] as a JSON array of
    {"page_content": "...", "metadata": {...}} objects. This function
    parses that representation and returns clean text the LLM can read.

    :param messages: List of messages
    :returns: Formatted context text, or empty string if none found
    """
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            raw = msg.content if hasattr(msg, "content") else ""
            if not raw:
                return ""
            docs = _parse_tool_message_documents(raw)
            if not docs:
                return ""  # Empty tool result — no context available
            parts = []
            for i, doc in enumerate(docs, 1):
                page_content = doc.get("page_content", "")
                metadata = doc.get("metadata", {})
                title = metadata.get("title", "")
                source_id = metadata.get("source_id", "")
                header = f"[Document {i}]"
                if title:
                    header += f" {title}"
                if source_id:
                    header += f" ({source_id})"
                parts.append(f"{header}\n{page_content}")
            return "\n\n".join(parts)

    return ""
