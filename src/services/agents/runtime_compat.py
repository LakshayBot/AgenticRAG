"""Compatibility layer for LangGraph Runtime.

The Runtime class is part of LangGraph Cloud/Studio and not available  
in the open-source version. This provides a simple type-compatible wrapper.
"""

from typing import Generic, TypeVar

T = TypeVar("T")


class Runtime(Generic[T]):
    """Type-safe runtime context wrapper for LangGraph nodes.
    
    This is a compatibility layer that mimics the LangGraph Cloud Runtime API
    for use with the open-source version of LangGraph.
    """
    
    def __init__(self, context: T):
        self.context = context
