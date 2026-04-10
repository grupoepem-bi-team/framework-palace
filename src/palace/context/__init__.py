"""
Palace Framework - Context Management Module

This module provides context management capabilities for the Palace framework,
including project context, session management, and context retrieval from
memory.

Components:
    - ContextManager: Main context management interface
    - ProjectContextManager: Project-specific context handling
    - ProjectLoader: Loads project context from /ai_context/ directory
    - ContextBuilder: Combines project + memory + session + task context
    - ContextRetriever: RAG-based context retrieval
    - SessionManager: Session lifecycle management

The context module is responsible for:
    - Managing project-level context (configuration, ADRs, patterns)
    - Maintaining session state and conversation history
    - Retrieving relevant context from memory (RAG)
    - Loading project files from /ai_context/ (architecture, stack, conventions)
    - Providing enriched context to agents during execution
"""

# Main context manager
# Context builder (combines all sources)
from palace.context.builder import ContextBuilder

# Project loader (loads /ai_context/ files)
from palace.context.loader import ProjectLoader
from palace.context.manager import ContextManager, ProjectContextManager

# Context retrieval (RAG)
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
    # Builder
    "ContextBuilder",
    # Loader
    "ProjectLoader",
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
