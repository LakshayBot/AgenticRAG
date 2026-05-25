import logging
import time
from functools import partial
from typing import Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langfuse.langchain import CallbackHandler
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.langfuse.client import LangfuseTracer
from src.services.ollama.client import OllamaClient
from src.services.opensearch.client import OpenSearchClient

from .config import GraphConfig
from .context import Context
from .context_holder import set_current_context, MockRuntime, get_current_context
from .nodes import (
    ainvoke_generate_answer_step,
    ainvoke_grade_documents_step,
    ainvoke_guardrail_step,
    ainvoke_out_of_scope_step,
    ainvoke_retrieve_step,
    ainvoke_rewrite_query_step,
    continue_after_guardrail,
)
from .state import AgentState
from .tools import create_retriever_tool

logger = logging.getLogger(__name__)


class AgenticRAGService:
    """Agentic RAG service

    This implementation uses:
    - context_schema for dependency injection
    - Runtime[Context] for type-safe access in nodes
    - Direct client invocation (no pre-built runnables)
    - Lightweight nodes as pure functions
    """

    def __init__(
        self,
        opensearch_client: OpenSearchClient,
        ollama_client: OllamaClient,
        embeddings_client: JinaEmbeddingsClient,
        langfuse_tracer: Optional[LangfuseTracer] = None,
        graph_config: Optional[GraphConfig] = None,
    ):
        """Initialize agentic RAG service.

        :param opensearch_client: Client for document search
        :param ollama_client: Client for LLM generation
        :param embeddings_client: Client for embeddings
        :param langfuse_tracer: Optional Langfuse tracer
        :param graph_config: Configuration for graph execution
        """
        self.opensearch = opensearch_client
        self.ollama = ollama_client
        self.embeddings = embeddings_client
        self.langfuse_tracer = langfuse_tracer
        self.graph_config = graph_config or GraphConfig()
        self.memory = MemorySaver()

        logger.info("Initializing AgenticRAGService with configuration:")
        logger.info(f"  Model: {self.graph_config.model}")
        logger.info(f"  Top-k: {self.graph_config.top_k}")
        logger.info(f"  Hybrid search: {self.graph_config.use_hybrid}")
        logger.info(f"  Max retrieval attempts: {self.graph_config.max_retrieval_attempts}")
        logger.info(f"  Guardrail threshold: {self.graph_config.guardrail_threshold}")

        # Build graph once (no runnables needed!)
        self.graph = self._build_graph()
        logger.info("✓ AgenticRAGService initialized successfully")

    def _build_graph(self):
        """Build and compile the LangGraph workflow.

        Nodes access runtime context via thread-local storage.

        :returns: Compiled graph ready for invocation
        """
        logger.info("Building LangGraph workflow")

        # Create workflow with AgentState only
        workflow = StateGraph(AgentState)

        # Create tools (these still need to be created upfront for ToolNode)
        retriever_tool = create_retriever_tool(
            opensearch_client=self.opensearch,
            embeddings_client=self.embeddings,
            top_k=self.graph_config.top_k,
            use_hybrid=self.graph_config.use_hybrid,
        )
        tools = [retriever_tool]

        # Add nodes - they'll access context via thread-local storage through wrapper
        logger.info("Adding nodes to workflow graph")

        # Create wrapper functions that provide MockRuntime to nodes
        mock_runtime = MockRuntime()

        def wrap_node(node_func):
            """Wrap node function to inject MockRuntime."""

            async def wrapper(state):
                return await node_func(state, mock_runtime)

            return wrapper

        workflow.add_node("guardrail", wrap_node(ainvoke_guardrail_step))
        workflow.add_node("out_of_scope", wrap_node(ainvoke_out_of_scope_step))
        workflow.add_node("retrieve", wrap_node(ainvoke_retrieve_step))
        workflow.add_node("tool_retrieve", ToolNode(tools))
        workflow.add_node("grade_documents", wrap_node(ainvoke_grade_documents_step))
        workflow.add_node("rewrite_query", wrap_node(ainvoke_rewrite_query_step))
        workflow.add_node("generate_answer", wrap_node(ainvoke_generate_answer_step))

        # Add edges
        logger.info("Configuring graph edges and routing logic")

        # Start → guardrail validation
        workflow.add_edge(START, "guardrail")

        # Guardrail → route based on score
        workflow.add_conditional_edges(
            "guardrail",
            lambda state: continue_after_guardrail(state, mock_runtime),
            {
                "continue": "retrieve",
                "out_of_scope": "out_of_scope",
            },
        )

        # Out of scope → END
        workflow.add_edge("out_of_scope", END)

        # Retrieve node creates tool call
        workflow.add_conditional_edges(
            "retrieve",
            tools_condition,
            {
                "tools": "tool_retrieve",
                END: END,
            },
        )

        # After tool retrieval → grade documents
        workflow.add_edge("tool_retrieve", "grade_documents")

        # After grading → route based on relevance
        workflow.add_conditional_edges(
            "grade_documents",
            lambda state: state.get("routing_decision", "generate_answer"),
            {
                "generate_answer": "generate_answer",
                "rewrite_query": "rewrite_query",
            },
        )

        # After rewriting → try retrieve again
        workflow.add_edge("rewrite_query", "retrieve")

        # After answer generation → done
        workflow.add_edge("generate_answer", END)

        # Compile graph with in-memory checkpointer for conversation persistence
        logger.info("Compiling LangGraph workflow")
        compiled_graph = workflow.compile(checkpointer=self.memory)
        logger.info("✓ Graph compilation successful")

        return compiled_graph

    async def ask(
        self,
        query: str,
        user_id: str = "api_user",
        session_id: Optional[str] = None,
        model: Optional[str] = None,
        file_ids: Optional[list] = None,
        advisory_ids: Optional[list] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> dict:
        """Ask a question using agentic RAG.

        :param query: User question
        :param user_id: User identifier for tracing
        :param session_id: Stable session identifier for conversation continuity
        :param model: Optional model override
        :param file_ids: Optional list of file IDs to filter search
        :param advisory_ids: Optional list of GHSA IDs to filter search
        :param conversation_history: Optional list of prior turns [{"role": "user"|"assistant", "content": "..."}]
        :returns: Dictionary with answer, sources, reasoning steps, and metadata
        :raises ValueError: If query is empty
        """
        model_to_use = model or self.graph_config.model

        logger.info("=" * 80)
        logger.info("Starting Agentic RAG Request")
        logger.info(f"Query: {query}")
        logger.info(f"User ID: {user_id}")
        logger.info(f"Session ID: {session_id or 'not provided — using user_id'}")
        logger.info(f"Model: {model_to_use}")
        logger.info(f"File IDs filter: {file_ids if file_ids else 'None (search all documents)'}")
        logger.info(f"Advisory IDs filter: {advisory_ids if advisory_ids else 'None'}")
        logger.info(f"Conversation history turns: {len(conversation_history) if conversation_history else 0}")
        logger.info("=" * 80)

        # Validate input
        if not query or len(query.strip()) == 0:
            logger.error("Empty query received")
            raise ValueError("Query cannot be empty")

        # Create trace if Langfuse is enabled (v4 SDK)
        trace = None
        if self.langfuse_tracer and self.langfuse_tracer.client:
            logger.info("Creating Langfuse trace (v4 SDK)")
            try:
                trace = self.langfuse_tracer.client.start_observation(
                    name="agentic_rag_request",
                    as_type="agent",
                    input={"query": query},
                    metadata={
                        "env": self.graph_config.settings.environment,
                        "service": "agentic_rag",
                        "top_k": self.graph_config.top_k,
                        "use_hybrid": self.graph_config.use_hybrid,
                        "model": model_to_use,
                        "user_id": user_id,
                        "session_id": f"session_{user_id}",
                    },
                )
                logger.debug(f"Langfuse trace created: {trace}")
            except Exception as e:
                logger.warning(f"Failed to create Langfuse trace: {e}")
                trace = None

        try:
            return await self._run_workflow(query, model_to_use, user_id, session_id, trace, file_ids, advisory_ids, conversation_history)
        except Exception as e:
            logger.error(f"Error in Agentic RAG execution: {str(e)}")
            logger.exception("Full traceback:")
            raise

    async def _run_workflow(
        self,
        query: str,
        model_to_use: str,
        user_id: str,
        session_id: Optional[str],
        trace,
        file_ids: Optional[list] = None,
        advisory_ids: Optional[list] = None,
        conversation_history: Optional[List[dict]] = None,
    ) -> dict:
        """Execute the workflow with the given trace context."""
        try:
            start_time = time.time()

            logger.info("Invoking LangGraph workflow")

            # Build prior conversation messages (last 6 turns max = 3 user+assistant pairs)
            prior_messages = []
            if conversation_history:
                for turn in conversation_history[-6:]:
                    role = turn.get("role", "")
                    content = turn.get("content", "")
                    if not content:
                        continue
                    if role == "user":
                        prior_messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        prior_messages.append(AIMessage(content=content))

            # State initialization — prior history prepended so LLM has context
            state_input = {
                "messages": prior_messages + [HumanMessage(content=query)],
                "retrieval_attempts": 0,
                "guardrail_result": None,
                "routing_decision": None,
                "sources": None,
                "relevant_sources": [],
                "relevant_tool_artefacts": None,
                "grading_results": [],
                "metadata": {},
                "original_query": None,
                "rewritten_query": None,
            }

            # Runtime context (dependencies)
            runtime_context = Context(
                ollama_client=self.ollama,
                opensearch_client=self.opensearch,
                embeddings_client=self.embeddings,
                langfuse_tracer=self.langfuse_tracer,
                trace=trace,
                langfuse_enabled=self.langfuse_tracer is not None and self.langfuse_tracer.client is not None,
                model_name=model_to_use,
                temperature=self.graph_config.temperature,
                top_k=self.graph_config.top_k,
                max_retrieval_attempts=self.graph_config.max_retrieval_attempts,
                guardrail_threshold=self.graph_config.guardrail_threshold,
                file_ids=file_ids,  # Pass file_ids to context
                advisory_ids=advisory_ids,  # Pass advisory_ids to context
            )

            # Set context in thread-local storage for nodes to access
            set_current_context(runtime_context)

            # Stable thread_id — uses session_id from frontend so conversation persists
            # across messages within the same session. Falls back to user_id if not provided.
            stable_thread_id = f"session_{session_id}" if session_id else f"user_{user_id}"
            config = {
                "configurable": {"thread_id": stable_thread_id},
            }

            # Add CallbackHandler for automatic LLM tracing
            if self.langfuse_tracer and trace:
                try:
                    callback_handler = CallbackHandler()
                    config["callbacks"] = [callback_handler]
                    logger.info("✓ CallbackHandler added (will auto-link to current trace)")
                except Exception as e:
                    logger.warning(f"Failed to create CallbackHandler: {e}")

            result = await self.graph.ainvoke(
                state_input,
                config=config,
            )

            execution_time = time.time() - start_time
            logger.info(f"✓ Graph execution completed in {execution_time:.2f}s")

            # Extract results
            answer = self._extract_answer(result)
            sources = self._extract_sources(result)
            retrieval_attempts = result.get("retrieval_attempts", 0)
            reasoning_steps = self._extract_reasoning_steps(result)

            # Update trace (cleanup handled by context manager)
            if trace:
                trace.update(
                    output={
                        "answer": answer,
                        "sources_count": len(sources),
                        "retrieval_attempts": retrieval_attempts,
                        "reasoning_steps": reasoning_steps,
                        "execution_time": execution_time,
                    }
                )
                trace.end()
                self.langfuse_tracer.flush()

            logger.info("=" * 80)
            logger.info("Agentic RAG Request Completed Successfully")
            logger.info(f"Answer length: {len(answer)} characters")
            logger.info(f"Sources found: {len(sources)}")
            logger.info(f"Retrieval attempts: {retrieval_attempts}")
            logger.info(f"Execution time: {execution_time:.2f}s")
            logger.info("=" * 80)

            return {
                "query": query,
                "answer": answer,
                "sources": sources,
                "reasoning_steps": reasoning_steps,
                "retrieval_attempts": retrieval_attempts,
                "rewritten_query": result.get("rewritten_query"),
                "execution_time": execution_time,
                "guardrail_score": result.get("guardrail_result").score if result.get("guardrail_result") else None,
            }

        except Exception as e:
            logger.error(f"Error in workflow execution: {str(e)}")
            logger.exception("Full traceback:")

            # Update trace with error (cleanup handled by context manager)
            if trace:
                trace.update(output={"error": str(e)}, level="ERROR")
                trace.end()
                self.langfuse_tracer.flush()

            raise

        finally:
            # Always reset context after graph execution to prevent bleed across concurrent requests
            set_current_context(None)

    def _extract_answer(self, result: dict) -> str:
        """Extract final answer from graph result."""
        messages = result.get("messages", [])
        if not messages:
            return "No answer generated."

        final_message = messages[-1]
        return final_message.content if hasattr(final_message, "content") else str(final_message)

    def _extract_sources(self, result: dict) -> List[dict]:
        """Extract sources from graph result.

        Parses sources from the ToolMessage content in messages, since
        relevant_sources in state is not populated by any node.
        """
        import json

        sources = []
        messages = result.get("messages", [])

        for msg in messages:
            if not isinstance(msg, ToolMessage):
                continue
            if getattr(msg, "name", None) != "retrieve_papers":
                continue
            raw = msg.content if hasattr(msg, "content") else ""
            if not raw:
                continue
            try:
                docs = json.loads(raw)
                if not isinstance(docs, list):
                    continue
            except (json.JSONDecodeError, TypeError):
                continue
            for doc in docs:
                metadata = doc.get("metadata", {})
                source_id = metadata.get("source_id", "")
                if not source_id:
                    continue
                authors = metadata.get("authors", [])
                if isinstance(authors, str):
                    authors = [authors] if authors else []
                chunk_text = doc.get("page_content", "")
                sources.append(
                    {
                        "sourceId": source_id,
                        "title": metadata.get("title", ""),
                        "authors": authors,
                        "chunkText": chunk_text,
                        "chunkIndex": 0,
                        "score": float(metadata.get("score", 0.0)),
                    }
                )

        return sources

    def _extract_reasoning_steps(self, result: dict) -> List[str]:
        """Extract reasoning steps from graph result."""
        steps = []
        retrieval_attempts = result.get("retrieval_attempts", 0)
        guardrail_result = result.get("guardrail_result")
        grading_results = result.get("grading_results", [])

        if guardrail_result:
            steps.append(f"Validated query scope (score: {guardrail_result.score}/100)")

        if retrieval_attempts > 0:
            steps.append(f"Retrieved documents ({retrieval_attempts} attempt(s))")

        if grading_results:
            relevant_count = sum(1 for g in grading_results if g.is_relevant)
            steps.append(f"Graded documents ({relevant_count} relevant)")

        if result.get("rewritten_query"):
            steps.append("Rewritten query for better results")

        steps.append("Generated answer from context")

        return steps

    def get_graph_visualization(self) -> bytes:
        """Get the LangGraph workflow visualization as PNG.

        This method generates a visual representation of the graph workflow
        using mermaid diagram format, then converts it to PNG.

        :returns: PNG image bytes
        :raises ImportError: If required dependencies (pygraphviz/graphviz) are not installed
        :raises Exception: If graph visualization generation fails

        Example:
            >>> service = AgenticRAGService(...)
            >>> png_bytes = service.get_graph_visualization()
            >>> with open("graph.png", "wb") as f:
            ...     f.write(png_bytes)
        """
        try:
            logger.info("Generating graph visualization as PNG")
            png_bytes = self.graph.get_graph().draw_mermaid_png()
            logger.info(f"✓ Generated PNG visualization ({len(png_bytes)} bytes)")
            return png_bytes
        except ImportError as e:
            logger.error(f"Failed to generate visualization - missing dependencies: {e}")
            logger.error("Install with: pip install pygraphviz or apt-get install graphviz")
            raise ImportError(
                "Graph visualization requires pygraphviz. Install with: pip install pygraphviz (requires graphviz system package)"
            ) from e
        except Exception as e:
            logger.error(f"Failed to generate graph visualization: {e}")
            raise

    def get_graph_mermaid(self) -> str:
        """Get the LangGraph workflow as a mermaid diagram string.

        This method generates the graph workflow representation in mermaid
        diagram syntax, which can be rendered in markdown or mermaid viewers.

        :returns: Mermaid diagram syntax as string

        Example:
            >>> service = AgenticRAGService(...)
            >>> mermaid = service.get_graph_mermaid()
            >>> print(mermaid)
            graph TD
                __start__ --> guardrail
                ...
        """
        try:
            logger.info("Generating graph as mermaid diagram")
            mermaid_str = self.graph.get_graph().draw_mermaid()
            logger.info(f"✓ Generated mermaid diagram ({len(mermaid_str)} characters)")
            return mermaid_str
        except Exception as e:
            logger.error(f"Failed to generate mermaid diagram: {e}")
            raise

    def get_graph_ascii(self) -> str:
        """Get ASCII representation of the graph.

        This method generates a simple ASCII art representation of the
        graph structure, useful for quick inspection in terminals.

        :returns: ASCII art representation of the graph

        Example:
            >>> service = AgenticRAGService(...)
            >>> print(service.get_graph_ascii())
        """
        try:
            logger.info("Generating ASCII graph representation")
            ascii_str = self.graph.get_graph().print_ascii()
            logger.info("✓ Generated ASCII graph representation")
            return ascii_str
        except Exception as e:
            logger.error(f"Failed to generate ASCII graph: {e}")
            raise
