framework-palace/src/palace/core/types.py
```

```python
"""
Palace Framework - Core Types (Re-exported from models/domain_types)

This module re-exports domain types from models/domain_types.py.
The actual definitions are in models/domain_types.py (single source of truth).

This module maintains backward compatibility by re-exporting types.
All new code should import directly from palace.models.domain_types.

Imports:
    - AgentRole, TaskStatus, TaskPriority, MemoryType
    - AgentCapability, MessageType, ProjectStatus, SessionStatus
    - Identifiable protocol
"""

# Re-export domain types from models/domain_types.py
from palace.models.domain_types import (
    AgentCapability,
    AgentRole,
    Identifiable,
    MemoryType,
    MessageType,
    ProjectStatus,
    SessionStatus,
    TaskPriority,
    TaskStatus,
)

# Re-export for backward compatibility
__all__ = [
    # Domain Types
    "AgentRole",
    "TaskStatus",
    "TaskPriority",
    "MemoryType",
    "MessageType",
    "AgentCapability",
    "ProjectStatus",
    "SessionStatus",
    # Protocol
    "Identifiable",
]
```

---

Ahora voy a actualizar el archivo `__init__.py` del framework para que importe desde los nuevos lugares:
