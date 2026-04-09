"""
Palace Framework - FastAPI Application

Main API module that exposes all framework functionality via REST endpoints.

Endpoints:
    - /projects: Project management
    - /tasks: Task execution and monitoring
    - /sessions: Conversation sessions
    - /memory: Memory store access
    - /agents: Agent information and status
    - /health: Health check
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import structlog
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from palace.core.config import get_settings
from palace.core.exceptions import PalaceError
from palace.core.framework import ExecutionResult, PalaceFramework, ProjectStatus

logger = structlog.get_logger()
settings = get_settings()

# Global framework instance
_framework: Optional[PalaceFramework] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage framework lifecycle."""
    global _framework

    logger.info("api_starting", version=settings.app_version)

    # Initialize framework
    _framework = PalaceFramework(settings)
    await _framework.initialize()

    logger.info("framework_initialized")

    yield

    # Shutdown
    logger.info("api_shutting_down")
    if _framework:
        await _framework.shutdown()
    logger.info("api_shutdown_complete")


# =============================================================================
# Application Instance
# =============================================================================

app = FastAPI(
    title="Palace Framework API",
    description="""
    Multi-agent intelligent framework for software development.

    ## Features

    - **Multi-Agent Orchestration**: Backend, Frontend, DevOps, Infra, DBA, QA, Designer, Reviewer
    - **Vector Memory**: Semantic context retrieval and storage
    - **Project Context**: Isolated context per project
    - **Task Management**: Create, execute, and monitor tasks

    ## Architecture

    The framework uses a central orchestrator to route tasks to specialized agents
    based on task requirements and agent capabilities.
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Dependency Injection
# =============================================================================


def get_framework() -> PalaceFramework:
    """Get the framework instance."""
    if _framework is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Framework not initialized"
        )
    return _framework


# =============================================================================
# Request/Response Models
# =============================================================================


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Project description", max_length=500)

    # Technology stack (optional)
    backend_framework: Optional[str] = Field(None, description="e.g., fastapi, django")
    frontend_framework: Optional[str] = Field(None, description="e.g., react, vue")
    database: Optional[str] = Field(None, description="e.g., postgresql, mysql")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my-api-project",
                "description": "A new REST API project",
                "backend_framework": "fastapi",
                "database": "postgresql",
            }
        }


class ProjectResponse(BaseModel):
    """Response for project operations."""

    project_id: str = Field(..., description="Unique project identifier")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: str = Field(..., description="Project status")
    created_at: str = Field(..., description="Creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_abc123",
                "name": "my-api-project",
                "description": "A new REST API project",
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
            }
        }


class TaskCreateRequest(BaseModel):
    """Request to create and execute a task."""

    task: str = Field(..., description="Task description", min_length=10)
    project_id: str = Field(..., description="Project identifier")
    session_id: Optional[str] = Field(
        None, description="Session identifier for conversation continuity"
    )
    agent_hint: Optional[str] = Field(None, description="Optional hint for agent routing")
    priority: str = Field("normal", description="Task priority: low, normal, high, critical")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context data")

    class Config:
        json_schema_extra = {
            "example": {
                "task": "Create a REST endpoint for user management with CRUD operations",
                "project_id": "proj_abc123",
                "session_id": "sess_xyz789",
                "priority": "normal",
            }
        }


class TaskResponse(BaseModel):
    """Response for task operations."""

    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    result: Optional[str] = Field(None, description="Task result content")
    agent_used: Optional[str] = Field(None, description="Agent that executed the task")
    execution_time: float = Field(..., description="Execution time in seconds")
    artifacts: List[Dict[str, Any]] = Field(default_factory=list, description="Generated artifacts")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_def456",
                "status": "completed",
                "result": "Endpoint created successfully...",
                "agent_used": "backend",
                "execution_time": 12.5,
                "artifacts": [{"path": "src/api/users.py", "type": "code"}],
                "metadata": {"tokens_used": 1500},
            }
        }


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""

    project_id: str = Field(..., description="Project identifier")
    initial_context: Optional[Dict[str, Any]] = Field(None, description="Initial session context")


class SessionResponse(BaseModel):
    """Response for session operations."""

    session_id: str = Field(..., description="Session identifier")
    project_id: str = Field(..., description="Associated project")
    created_at: str = Field(..., description="Creation timestamp")
    message_count: int = Field(..., description="Number of messages in session")


class MemoryQueryRequest(BaseModel):
    """Request to query memory."""

    query: str = Field(..., description="Search query", min_length=3)
    project_id: str = Field(..., description="Project identifier")
    memory_type: Optional[str] = Field(
        None, description="Memory type: episodic, semantic, procedural"
    )
    top_k: int = Field(5, description="Number of results to return", ge=1, le=20)


class MemoryEntryRequest(BaseModel):
    """Request to add a memory entry."""

    project_id: str = Field(..., description="Project identifier")
    content: str = Field(..., description="Content to store", min_length=10)
    memory_type: str = Field("semantic", description="Memory type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MemoryResponse(BaseModel):
    """Response for memory operations."""

    entries: List[Dict[str, Any]] = Field(..., description="Retrieved memory entries")
    total: int = Field(..., description="Total number of entries found")


class AgentInfoResponse(BaseModel):
    """Response with agent information."""

    name: str = Field(..., description="Agent name")
    model: str = Field(..., description="LLM model used")
    description: str = Field(..., description="Agent description")
    capabilities: List[str] = Field(..., description="Agent capabilities")
    tools: List[str] = Field(..., description="Available tools")
    status: str = Field(..., description="Current status")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    framework_initialized: bool = Field(..., description="Framework initialization status")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(PalaceError)
async def palace_exception_handler(request, exc: PalaceError):
    """Handle Palace framework exceptions."""
    logger.error("palace_error", error=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=exc.code, message=exc.message, details=exc.details
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception("unhandled_error", error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details={"original_error": str(exc)},
        ).model_dump(),
    )


# =============================================================================
# Health Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check API health status.

    Returns basic health information about the API and framework.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        framework_initialized=_framework is not None and _framework._initialized,
    )


@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.

    Returns basic information about the Palace Framework API.
    """
    return {
        "name": "Palace Framework API",
        "version": settings.app_version,
        "description": "Multi-agent intelligent framework for software development",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# =============================================================================
# Project Endpoints
# =============================================================================


@app.post(
    "/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Projects"],
)
async def create_project(
    request: ProjectCreateRequest, framework: PalaceFramework = Depends(get_framework)
):
    """
    Create a new project.

    Creates a new project with the specified configuration and
    initializes its context in the memory store.
    """
    logger.info("creating_project", name=request.name)

    # TODO: Implement project creation via context manager
    project_id = f"proj_{request.name.lower().replace(' ', '_')}"

    return ProjectResponse(
        project_id=project_id,
        name=request.name,
        description=request.description,
        status="active",
        created_at="2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
    )


@app.get("/projects/{project_id}", response_model=ProjectResponse, tags=["Projects"])
async def get_project(project_id: str, framework: PalaceFramework = Depends(get_framework)):
    """
    Get project information.

    Returns details about a specific project including its
    configuration and current status.
    """
    status_info = await framework.get_project_status(project_id)

    return ProjectResponse(
        project_id=project_id,
        name=project_id,  # TODO: Get from context
        description=None,
        status=status_info.status,
        created_at=status_info.last_activity,
    )


@app.get("/projects", response_model=List[ProjectResponse], tags=["Projects"])
async def list_projects(framework: PalaceFramework = Depends(get_framework)):
    """
    List all projects.

    Returns a list of all active projects in the framework.
    """
    project_ids = framework._orchestrator.list_active_projects()

    return [
        ProjectResponse(
            project_id=pid,
            name=pid,
            description=None,
            status="active",
            created_at="2024-01-01T00:00:00Z",
        )
        for pid in project_ids
    ]


@app.get("/projects/{project_id}/status", response_model=ProjectStatus, tags=["Projects"])
async def get_project_status(project_id: str, framework: PalaceFramework = Depends(get_framework)):
    """
    Get detailed project status.

    Returns comprehensive status information including
    active tasks and recent activity.
    """
    return await framework.get_project_status(project_id)


# =============================================================================
# Task Endpoints
# =============================================================================


@app.post(
    "/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"]
)
async def create_task(
    request: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    framework: PalaceFramework = Depends(get_framework),
):
    """
    Create and execute a task.

    Submits a task to the framework for execution. The orchestrator
    will route it to the appropriate agent based on the task description.

    The task is executed asynchronously. For long-running tasks,
    use the task_id to poll for status.
    """
    logger.info("creating_task", project_id=request.project_id, task_preview=request.task[:50])

    result = await framework.execute(
        task=request.task,
        project_id=request.project_id,
        session_id=request.session_id,
        agent_hint=request.agent_hint,
        context=request.context,
    )

    return TaskResponse(
        task_id=result.task_id,
        status=result.status,
        result=result.result,
        agent_used=result.agent_used,
        execution_time=result.execution_time,
        artifacts=result.metadata.get("artifacts", []),
        metadata=result.metadata,
    )


@app.get("/tasks/{task_id}", response_model=TaskResponse, tags=["Tasks"])
async def get_task_status(
    task_id: str,
    project_id: str = Query(..., description="Project identifier"),
    framework: PalaceFramework = Depends(get_framework),
):
    """
    Get task status and result.

    Returns the current status and result (if completed) of a task.
    """
    # TODO: Implement task status retrieval
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task {task_id} not found")


# =============================================================================
# Session Endpoints
# =============================================================================


@app.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sessions"],
)
async def create_session(
    request: SessionCreateRequest, framework: PalaceFramework = Depends(get_framework)
):
    """
    Create a new conversation session.

    Creates a new session for multi-turn conversations within a project.
    Sessions maintain conversation history and context.
    """
    logger.info("creating_session", project_id=request.project_id)

    # TODO: Implement session creation via context manager
    session_id = f"sess_{request.project_id}"

    return SessionResponse(
        session_id=session_id,
        project_id=request.project_id,
        created_at="2024-01-01T00:00:00Z",
        message_count=0,
    )


@app.get("/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
async def get_session(session_id: str, framework: PalaceFramework = Depends(get_framework)):
    """
    Get session information.

    Returns details about a specific session including
    message count and creation time.
    """
    # TODO: Implement session retrieval
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found"
    )


@app.get("/sessions/{session_id}/history", tags=["Sessions"])
async def get_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    framework: PalaceFramework = Depends(get_framework),
):
    """
    Get session conversation history.

    Returns the conversation history for a session with pagination.
    """
    # TODO: Implement history retrieval from memory
    return {"session_id": session_id, "messages": [], "total": 0, "limit": limit, "offset": offset}


# =============================================================================
# Memory Endpoints
# =============================================================================


@app.post("/memory/query", response_model=MemoryResponse, tags=["Memory"])
async def query_memory(
    request: MemoryQueryRequest, framework: PalaceFramework = Depends(get_framework)
):
    """
    Query the vector memory store.

    Performs a semantic search over the memory store to find
    relevant context for the given query.
    """
    logger.info("querying_memory", project_id=request.project_id, query_preview=request.query[:50])

    # TODO: Implement memory query
    return MemoryResponse(entries=[], total=0)


@app.post("/memory/entries", status_code=status.HTTP_201_CREATED, tags=["Memory"])
async def add_memory_entry(
    request: MemoryEntryRequest, framework: PalaceFramework = Depends(get_framework)
):
    """
    Add an entry to memory.

    Stores a new entry in the memory store with the specified
    type and metadata.
    """
    logger.info(
        "adding_memory_entry", project_id=request.project_id, memory_type=request.memory_type
    )

    # TODO: Implement memory entry addition
    return {
        "status": "created",
        "project_id": request.project_id,
        "memory_type": request.memory_type,
    }


@app.get("/memory/types", tags=["Memory"])
async def list_memory_types():
    """
    List available memory types.

    Returns the different types of memory storage available
    in the framework.
    """
    return {
        "types": [
            {"name": "episodic", "description": "Conversation history and task results"},
            {"name": "semantic", "description": "Knowledge, ADRs, and patterns"},
            {"name": "procedural", "description": "Scripts and reusable procedures"},
            {"name": "project", "description": "Project-specific context"},
        ]
    }


# =============================================================================
# Agent Endpoints
# =============================================================================


@app.get("/agents", response_model=List[AgentInfoResponse], tags=["Agents"])
async def list_agents(framework: PalaceFramework = Depends(get_framework)):
    """
    List all available agents.

    Returns information about all agents registered in the framework
    including their capabilities and current status.
    """
    agents = await framework.list_agents()

    # TODO: Get actual agent info from orchestrator
    agent_info = [
        AgentInfoResponse(
            name="backend",
            model="qwen3-coder-next",
            description="Backend development specialist",
            capabilities=["backend_development", "testing"],
            tools=["shell", "file_read", "file_write", "linter", "test_runner"],
            status="idle",
        ),
        AgentInfoResponse(
            name="frontend",
            model="qwen3-coder-next",
            description="Frontend development specialist",
            capabilities=["frontend_development", "testing", "ui_ux_design"],
            tools=["shell", "file_read", "file_write", "linter", "test_runner"],
            status="idle",
        ),
        AgentInfoResponse(
            name="devops",
            model="qwen3.5",
            description="DevOps and CI/CD specialist",
            capabilities=["devops", "infrastructure_as_code"],
            tools=["shell", "file_write", "git", "docker", "kubernetes"],
            status="idle",
        ),
        AgentInfoResponse(
            name="dba",
            model="deepseek-v3.2",
            description="Database administration specialist",
            capabilities=["database_administration"],
            tools=["shell", "file_read", "file_write", "sql_runner"],
            status="idle",
        ),
        AgentInfoResponse(
            name="qa",
            model="gemma4:31b",
            description="Quality assurance specialist",
            capabilities=["quality_assurance", "testing"],
            tools=["linter", "test_runner", "coverage_analyzer"],
            status="idle",
        ),
        AgentInfoResponse(
            name="reviewer",
            model="mistral-large",
            description="Code review and architecture specialist",
            capabilities=["code_review", "architecture"],
            tools=["file_read", "linter", "git"],
            status="idle",
        ),
    ]

    return agent_info


@app.get("/agents/{agent_name}", response_model=AgentInfoResponse, tags=["Agents"])
async def get_agent_info(agent_name: str, framework: PalaceFramework = Depends(get_framework)):
    """
    Get information about a specific agent.

    Returns detailed information about a specific agent
    including capabilities, tools, and current status.
    """
    # TODO: Implement agent info retrieval from orchestrator
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_name} not found"
    )


# =============================================================================
# Development/Debug Endpoints (only in development)
# =============================================================================

if settings.is_development():

    @app.post("/debug/reload", tags=["Debug"])
    async def reload_framework(framework: PalaceFramework = Depends(get_framework)):
        """Reload framework configuration (development only)."""
        await framework.shutdown()
        await framework.initialize()
        return {"status": "reloaded"}

    @app.get("/debug/config", tags=["Debug"])
    async def get_config():
        """Get current configuration (development only)."""
        return {
            "ollama": {"base_url": settings.ollama.base_url, "timeout": settings.ollama.timeout},
            "models": {
                "orchestrator": settings.model.orchestrator,
                "backend": settings.model.backend,
                "frontend": settings.model.frontend,
                "devops": settings.model.devops,
                "dba": settings.model.dba,
                "qa": settings.model.qa,
                "reviewer": settings.model.reviewer,
            },
            "memory": {
                "store_type": settings.memory.store_type,
                "collection_name": settings.memory.collection_name,
            },
        }


# =============================================================================
# Main Entry Point (for direct execution)
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "palace.api.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.debug,
        workers=settings.api.workers,
    )
