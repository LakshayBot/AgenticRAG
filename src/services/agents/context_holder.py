"""Context storage for runtime context.

This module provides a way to pass runtime context to nodes without using LangGraph's context_schema,
which has serialization issues with client objects. Uses contextvars for async-safe storage.
"""
from contextvars import ContextVar
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import Context

_context_var: ContextVar[Optional["Context"]] = ContextVar('runtime_context', default=None)


def get_current_context() -> Optional["Context"]:
    """Get the current runtime context from context var."""
    return _context_var.get()


def set_current_context(context: "Context"):
    """Set the current runtime context in context var."""
    _context_var.set(context)


class MockRuntime:
    """Mock Runtime object that provides context from context var."""
    
    @property
    def context(self):
        return get_current_context()
