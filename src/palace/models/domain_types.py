"""
Palace Framework - Domain Types (Consolidated)

This module defines all core domain types used throughout the framework.
These types are shared across components and provide type safety.

This is the SINGLE SOURCE OF TRUTH for domain types.
Other modules should import from here, NOT define their own versions.

Components:
    - AgentRole: Roles that agents can play
    - TaskStatus: Lifecycle states for tasks
    - TaskPriority: Priority levels for scheduling
    - MemoryType: Types of memory storage
    - AgentCapability: Skills and competencies
    - MessageType: Types of messages in conversations
"""

from enum import Enum
from typing import Protocol


# =============================================================================
# Agent Roles
# =============================================================================

class AgentRole(str, Enum):
    """Roles that agents can play in the system."""

    ORCHESTRATOR = "orchestrator"
    BACKEND = "backend"
    FRONTEND = "frontend"
    DEVOPS = "devops"
    INFRA = "infra"
    DBA = "dba"
    QA = "qa"
    DESIGNER = "designer"
    REVIEWER = "reviewer"


# =============================================================================
# Task Status
# =============================================================================

class TaskStatus(str, Enum):
    """Status of a task in the execution pipeline."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVIEW = "review"
    WAITING = "waiting"
    DELEGATED = "delegated"


# =============================================================================
# Task Priority
# =============================================================================

class TaskPriority(int, Enum):
    """Priority levels for task scheduling."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


# =============================================================================
# Memory Type
# =============================================================================

class MemoryType(str, Enum):
    """Types of memory storage."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    PROJECT = "project"


# =============================================================================
# Message Type
# =============================================================================

class MessageType(str, Enum):
    """Types of messages in conversations."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


# =============================================================================
# Agent Capability
# =============================================================================

class AgentCapability(str, Enum):
    """
    Skills and competencies that agents can have.
    """

    # Development capabilities
    BACKEND_DEVELOPMENT = "backend_development"
    FRONTEND_DEVELOPMENT = "frontend_development"
    FULLSTACK_DEVELOPMENT = "fullstack_development"

    # Infrastructure capabilities
    INFRASTRUCTURE_AS_CODE = "infrastructure_as_code"
    DEVOPS = "devops"
    DATABASE_ADMINISTRATION = "database_administration"

    # Quality capabilities
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    QUALITY_ASSURANCE = "quality_assurance"

    # Design capabilities
    UI_UX_DESIGN = "ui_ux_design"


# =============================================================================
# Project Status
# =============================================================================

class ProjectStatus(str, Enum):
    """Status of a project."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    PAUSED = "paused"
    DELETED = "deleted"


# =============================================================================
# Session Status
# =============================================================================

class SessionStatus(str, Enum):
    """Status of a conversation session."""

    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"


# =============================================================================
# Utility Protocol
# =============================================================================

class Identifiable(Protocol):
    """Protocol for objects with an ID."""

    @property
    def id(self) -> str: ...
```

---
