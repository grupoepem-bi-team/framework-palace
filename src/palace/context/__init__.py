"""
Palace Framework - Context Management Module

This module provides context management capabilities for the Palace framework,
including project context, session management, and context retrieval from
memory.

Components:
    - ContextManager: Main context management interface
    - ProjectContextManager: Project-specific context handling
    - SessionManager: Session lifecycle management
    - ContextRetriever: RAG-based context retrieval

The context module is responsible for:
    - Managing project-level context (configuration, ADRs, patterns)
    - Maintaining session state and conversation history
    - Retrieving relevant context from memory (RAG)
    - Providing enriched context to agents during execution
"""

# Main context manager
from palace.context.manager import ContextManager, ProjectContextManager

# Context retrieval
from palace.context.retriever import ContextRetriever, RetrievalConfig

# Session management
from palace.context.session import SessionManager, SessionState

# Context types
from palace.context.types import (
    ContextEntry,
    ContextType,
    ProjectConfig,
    RetrievedContext,
    SessionConfig,
)

__all__ = [
    # Context Manager
    "ContextManager",
    "ProjectContextManager",
    # Session
    "SessionManager",
    "SessionState",
    # Retriever
    "ContextRetriever",
    "RetrievalConfig",
    # Types
    "ContextEntry",
    "ContextType",
    "ProjectConfig",
    "SessionConfig",
    "RetrievedContext",
]
