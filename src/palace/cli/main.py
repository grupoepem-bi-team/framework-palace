"""
Palace Framework - Command Line Interface

Main entry point for the Palace CLI. Provides commands for:
- Project management (init, status, list)
- Task execution (run, execute)
- Agent interaction (agents, info)
- Memory management (memory, query)
- Session handling (session, history)

Usage:
    palace init my-project
    palace run "Create a REST endpoint for user management"
    palace status
    palace agents
"""

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from palace.context.loader import ProjectLoader
from palace.core.config import get_settings
from palace.core.framework import PalaceFramework
from palace.memory.base import MemoryEntry, MemoryType, SearchQuery

# Create Typer app
app = typer.Typer(
    name="palace",
    help="Palace - Multi-agent intelligent framework for software development",
    no_args_is_help=True,
    add_completion=False,
)

# Rich console for output
console = Console()

# Global framework instance
_framework: Optional[PalaceFramework] = None


def get_framework() -> PalaceFramework:
    """Get or create the framework instance."""
    global _framework
    if _framework is None:
        settings = get_settings()
        _framework = PalaceFramework(settings)
        asyncio.run(_framework.initialize())
    return _framework


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


# =============================================================================
# Project Commands
# =============================================================================


@app.command("init")
def init_project(
    name: str = typer.Argument(..., help="Project name"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Project description"),
    backend: Optional[str] = typer.Option(None, "--backend", "-b", help="Backend framework"),
    frontend: Optional[str] = typer.Option(None, "--frontend", "-f", help="Frontend framework"),
    database: Optional[str] = typer.Option(None, "--db", help="Database type"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path to project directory"),
):
    """
    Initialize a new Palace project.

    Creates a new project with the specified configuration and
    initializes its context in the memory store.

    Examples:
        palace init my-api
        palace init my-app --backend fastapi --db postgresql
        palace init my-app --path /path/to/project
    """
    console.print(f"[bold blue]Initializing project:[/] {name}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project...", total=None)

        try:
            framework = get_framework()

            # Create project configuration
            config = {}
            if backend:
                config["backend_framework"] = backend
            if frontend:
                config["frontend_framework"] = frontend
            if database:
                config["database"] = database

            project_id = name.lower().replace(" ", "-")

            # Create project using context_manager directly
            context = run_async(
                framework._context_manager.create_project(
                    project_id=project_id,
                    name=name,
                    description=description,
                    config=config,
                )
            )

            progress.update(task, description="Project created!")

            # Attempt to load project context files from /ai_context/
            context_files_loaded = []
            project_path = Path(path) if path else Path.cwd() / project_id
            try:
                loader = ProjectLoader(project_path=project_path)
                _ = run_async(loader.load())
                if loader.is_loaded:
                    context_files_loaded = loader.loaded_files
                    progress.update(
                        task,
                        description=f"Loaded {len(context_files_loaded)} context files",
                    )
            except Exception:
                # Context loading is optional — don't fail project creation
                progress.update(task, description="Project created (no context files found)")

            # Build success message
            success_msg = (
                f"[bold green]Project '{name}' created successfully![/]\n\n"
                f"Project ID: {context.config.project_id}\n"
            )
            if context_files_loaded:
                success_msg += f"Context files loaded: {', '.join(context_files_loaded)}\n"
            success_msg += "\nUse 'palace run' to execute tasks."

            console.print(
                Panel.fit(
                    success_msg,
                    title="[bold]Palace Project[/]",
                    border_style="green",
                )
            )

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(1)


@app.command("status")
def project_status(
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Show project status.

    Displays information about the current or specified project,
    including active tasks, session count, and recent activity.

    Examples:
        palace status
        palace status --project my-api
    """
    try:
        framework = get_framework()
        settings = get_settings()

        # Use default project if not specified
        target_project = project_id or settings.cli.default_project

        status_info = run_async(framework.get_project_status(target_project))

        if json_output:
            console.print_json(json.dumps(status_info.to_dict(), indent=2))
        else:
            table = Table(title=f"Project Status: {target_project}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Project ID", status_info.project_id)
            table.add_row("Status", status_info.status)
            table.add_row("Active Tasks", str(status_info.active_tasks))
            table.add_row("Last Activity", status_info.last_activity)

            if status_info.context_summary:
                table.add_row("Context Summary", status_info.context_summary[:100] + "...")

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("list")
def list_projects(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    List all projects.

    Shows all projects registered in the framework.

    Examples:
        palace list
        palace list --json
    """
    try:
        framework = get_framework()
        projects = framework._orchestrator.list_active_projects()

        if json_output:
            console.print_json(json.dumps({"projects": projects}, indent=2))
        else:
            if not projects:
                console.print("[yellow]No projects found.[/]")
                return

            table = Table(title="Projects")
            table.add_column("#", style="dim")
            table.add_column("Project ID", style="cyan")

            for i, project in enumerate(projects, 1):
                table.add_row(str(i), project)

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


# =============================================================================
# Task Commands
# =============================================================================


@app.command("run")
def run_task(
    task: str = typer.Argument(..., help="Task description to execute"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    agent: Optional[str] = typer.Option(None, "--agent", "-a", help="Agent hint"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Execute a task through the framework.

    The orchestrator will analyze the task and route it to the
    appropriate agent based on the task description.

    Examples:
        palace run "Create a REST endpoint for user management"
        palace run "Add authentication to the API" --project my-api
        palace run "Write tests for user service" --agent qa
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    console.print(f"[bold blue]Executing task:[/] {task[:80]}...")
    console.print(f"[dim]Project: {target_project}[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_progress = progress.add_task("Processing...", total=None)

        try:
            framework = get_framework()

            result = run_async(
                framework.execute(
                    task=task,
                    project_id=target_project,
                    session_id=session,
                    agent_hint=agent,
                )
            )

            progress.stop()

            if json_output:
                console.print_json(json.dumps(result.to_dict(), indent=2))
            else:
                # Show result
                console.print()
                console.print(
                    Panel(
                        result.result[:500] + "..." if len(result.result) > 500 else result.result,
                        title=f"[bold]{result.agent_used}[/] Response",
                        border_style="green" if result.status == "success" else "red",
                    )
                )

                # Show metadata
                if verbose:
                    meta_table = Table(title="Execution Metadata")
                    meta_table.add_column("Property", style="cyan")
                    meta_table.add_column("Value", style="green")

                    meta_table.add_row("Task ID", result.task_id)
                    meta_table.add_row("Status", result.status)
                    meta_table.add_row("Agent", result.agent_used)
                    meta_table.add_row("Execution Time", f"{result.execution_time:.2f}s")

                    console.print(meta_table)

                # Show artifacts if any
                if result.metadata.get("artifacts"):
                    console.print("\n[bold]Generated Artifacts:[/]")
                    for artifact in result.metadata["artifacts"]:
                        console.print(f"  • {artifact.get('path', 'unknown')}")

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]Error:[/] {e}")
            if verbose:
                console.print_exception()
            raise typer.Exit(1)


# =============================================================================
# Agent Commands
# =============================================================================


@app.command("agents")
def list_agents(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    List all available agents.

    Shows information about all agents registered in the framework,
    including their models, capabilities, and current status.

    Examples:
        palace agents
        palace agents --json
    """
    try:
        framework = get_framework()
        agents = run_async(framework.list_agents())

        # Fallback agent info mapping (used when agent instances are unavailable)
        agent_info_fallback = {
            "backend": {
                "model": "qwen3-coder-next",
                "description": "Backend development specialist",
                "capabilities": ["backend_development", "testing"],
                "tools": ["shell", "file_read", "file_write", "linter", "test_runner"],
            },
            "frontend": {
                "model": "qwen3-coder-next",
                "description": "Frontend development specialist",
                "capabilities": ["frontend_development", "testing", "ui_ux_design"],
                "tools": ["shell", "file_read", "file_write", "linter", "test_runner"],
            },
            "devops": {
                "model": "qwen3.5",
                "description": "DevOps and CI/CD specialist",
                "capabilities": ["devops", "infrastructure_as_code"],
                "tools": ["shell", "file_write", "git", "docker", "kubernetes"],
            },
            "dba": {
                "model": "deepseek-v3.2",
                "description": "Database administration specialist",
                "capabilities": ["database_administration"],
                "tools": ["shell", "file_read", "file_write", "sql_runner"],
            },
            "qa": {
                "model": "gemma4:31b",
                "description": "Quality assurance specialist",
                "capabilities": ["quality_assurance", "testing"],
                "tools": ["linter", "test_runner", "coverage_analyzer"],
            },
            "reviewer": {
                "model": "mistral-large",
                "description": "Code review and architecture specialist",
                "capabilities": ["code_review", "architecture"],
                "tools": ["file_read", "linter", "git"],
            },
        }

        # Build agent info dynamically from orchestrator._agents
        agent_info = {}
        orchestrator = framework._orchestrator
        for agent_name in agents:
            if hasattr(orchestrator, "_agents") and agent_name in orchestrator._agents:
                agent = orchestrator._agents[agent_name]
                agent_info[agent_name] = {
                    "model": getattr(agent, "model", "unknown"),
                    "description": getattr(agent, "_get_description", lambda: "")()
                    if hasattr(agent, "_get_description")
                    else str(getattr(agent, "role", "")),
                    "capabilities": getattr(agent.capabilities, "to_list", lambda: [])()
                    if hasattr(agent, "capabilities") and hasattr(agent.capabilities, "to_list")
                    else [],
                    "tools": getattr(agent, "tools", []),
                }
            else:
                # Fallback to hardcoded info
                agent_info[agent_name] = agent_info_fallback.get(
                    agent_name,
                    {
                        "model": "unknown",
                        "description": "",
                        "capabilities": [],
                        "tools": [],
                    },
                )

        if json_output:
            console.print_json(json.dumps({"agents": agent_info}, indent=2))
        else:
            table = Table(title="Available Agents")
            table.add_column("Agent", style="cyan")
            table.add_column("Model", style="green")
            table.add_column("Description", style="white")
            table.add_column("Capabilities", style="yellow")

            for agent_name, info in agent_info.items():
                table.add_row(
                    agent_name,
                    info.get("model", "unknown"),
                    info.get("description", ""),
                    ", ".join(info.get("capabilities", [])[:3]),
                )

            console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@app.command("info")
def agent_info(
    agent_name: str = typer.Argument(..., help="Agent name"),
):
    """
    Show detailed information about an agent.

    Examples:
        palace info backend
        palace info qa
    """
    try:
        framework = get_framework()
        agents = run_async(framework.list_agents())

        # Fallback agent data (used when agent instances are unavailable)
        agent_data_fallback = {
            "backend": {
                "model": "qwen3-coder-next",
                "description": "Backend development specialist for APIs, services, and business logic",
                "capabilities": [
                    "backend_development",
                    "fullstack_development",
                    "testing",
                    "documentation",
                ],
                "tools": [
                    "shell",
                    "file_read",
                    "file_write",
                    "linter",
                    "test_runner",
                    "http_client",
                ],
                "frameworks": ["FastAPI", "Django", "Flask", "SQLAlchemy"],
            },
            "frontend": {
                "model": "qwen3-coder-next",
                "description": "Frontend development specialist for UI components and client-side logic",
                "capabilities": ["frontend_development", "testing", "ui_ux_design"],
                "tools": ["shell", "file_read", "file_write", "linter", "test_runner"],
                "frameworks": ["React", "Vue", "Angular", "TypeScript"],
            },
            "devops": {
                "model": "qwen3.5",
                "description": "DevOps specialist for CI/CD, deployment, and infrastructure",
                "capabilities": ["devops", "infrastructure_as_code", "documentation"],
                "tools": ["shell", "file_write", "git", "docker", "kubernetes"],
                "tools_detail": [
                    "GitHub Actions",
                    "GitLab CI",
                    "Docker",
                    "Kubernetes",
                    "Terraform",
                ],
            },
            "dba": {
                "model": "deepseek-v3.2",
                "description": "Database specialist for schema design, migrations, and optimization",
                "capabilities": ["database_administration"],
                "tools": ["shell", "file_read", "file_write", "sql_runner"],
                "databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis"],
            },
            "qa": {
                "model": "gemma4:31b",
                "description": "Quality assurance specialist for testing and code quality",
                "capabilities": ["quality_assurance", "testing"],
                "tools": ["linter", "test_runner", "coverage_analyzer"],
                "tools_detail": ["pytest", "jest", "cypress", "sonarqube"],
            },
            "reviewer": {
                "model": "mistral-large",
                "description": "Code review and architecture specialist",
                "capabilities": ["code_review", "architecture"],
                "tools": ["file_read", "linter", "git"],
            },
        }

        if agent_name not in agents:
            console.print(f"[bold red]Error:[/] Agent '{agent_name}' not found")
            console.print(f"Available agents: {', '.join(agents)}")
            raise typer.Exit(1)

        # Try to get actual agent info from orchestrator
        info = None
        orchestrator = framework._orchestrator
        if hasattr(orchestrator, "_agents") and agent_name in orchestrator._agents:
            agent = orchestrator._agents[agent_name]
            info = {
                "model": getattr(agent, "model", "unknown"),
                "description": getattr(agent, "_get_description", lambda: "")()
                if hasattr(agent, "_get_description")
                else str(getattr(agent, "role", "")),
                "capabilities": getattr(agent.capabilities, "to_list", lambda: [])()
                if hasattr(agent, "capabilities") and hasattr(agent.capabilities, "to_list")
                else [],
                "tools": getattr(agent, "tools", []),
            }

        # Fallback to hardcoded info if agent instance not available
        if info is None:
            info = agent_data_fallback.get(
                agent_name,
                {
                    "model": "unknown",
                    "description": "",
                    "capabilities": [],
                    "tools": [],
                },
            )

        console.print(Panel(f"[bold]{agent_name.upper()}[/] Agent", border_style="cyan"))
        console.print(f"\n[bold]Model:[/] {info['model']}")
        console.print(f"[bold]Description:[/] {info['description']}")

        console.print(f"\n[bold]Capabilities:[/]")
        for cap in info["capabilities"]:
            console.print(f"  • {cap}")

        console.print(f"\n[bold]Tools:[/]")
        for tool in info["tools"]:
            console.print(f"  • {tool}")

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


# =============================================================================
# Memory Commands
# =============================================================================


memory_app = typer.Typer(help="Memory management commands")
app.add_typer(memory_app, name="memory")


@memory_app.command("query")
def query_memory(
    query: str = typer.Argument(..., help="Search query"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results"),
    memory_type: Optional[str] = typer.Option(None, "--type", "-t", help="Memory type"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Query the memory store.

    Performs a semantic search over stored memories.

    Examples:
        palace memory query "authentication patterns"
        palace memory query "API design" --project my-api --top 10
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    console.print(f"[bold blue]Querying memory:[/] {query}")

    try:
        framework = get_framework()

        # Map string memory_type to MemoryType enum
        memory_type_map = {
            "episodic": MemoryType.EPISODIC,
            "semantic": MemoryType.SEMANTIC,
            "procedural": MemoryType.PROCEDURAL,
            "project": MemoryType.PROJECT,
        }

        mem_type = None
        if memory_type and memory_type in memory_type_map:
            mem_type = memory_type_map[memory_type]

        # Build the search query
        if mem_type is not None:
            search_query = SearchQuery(
                query=query,
                project_id=target_project,
                top_k=top_k,
                memory_types=[mem_type],
            )
        else:
            search_query = SearchQuery(
                query=query,
                project_id=target_project,
                top_k=top_k,
            )

        # Query memory
        results = run_async(framework._memory_store.search(search_query))

        # Helper to extract fields from SearchResult dataclass or dict
        def _get_result_field(result, field, default=None):
            if hasattr(result, field):
                return getattr(result, field, default)
            if isinstance(result, dict):
                return result.get(field, default)
            return default

        if json_output:
            results_data = []
            for r in results:
                if hasattr(r, "to_dict"):
                    results_data.append(r.to_dict())
                elif isinstance(r, dict):
                    results_data.append(r)
                else:
                    results_data.append(
                        {
                            f: getattr(r, f, None)
                            for f in ["entry_id", "content", "score", "memory_type", "metadata"]
                        }
                    )
            console.print_json(json.dumps({"results": results_data}, indent=2, default=str))
        else:
            if not results:
                console.print("[yellow]No results found.[/]")
                return

            console.print(f"\n[bold]Found {len(results)} results:[/]\n")

            for i, result in enumerate(results, 1):
                score = _get_result_field(result, "score", 0) or 0
                content = str(_get_result_field(result, "content", ""))[:200]

                console.print(f"[bold cyan]Result {i}[/] (score: {score:.3f})")
                console.print(f"  {content}...")
                console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@memory_app.command("add")
def add_memory(
    content: str = typer.Argument(..., help="Content to store"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    memory_type: str = typer.Option("semantic", "--type", "-t", help="Memory type"),
    title: Optional[str] = typer.Option(None, "--title", help="Entry title"),
):
    """
    Add an entry to memory.

    Examples:
        palace memory add "API uses JWT authentication" --project my-api
        palace memory add "Decision: Use PostgreSQL for primary DB" --type semantic
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    try:
        framework = get_framework()

        # Map string memory_type to MemoryType enum
        memory_type_map = {
            "episodic": MemoryType.EPISODIC,
            "semantic": MemoryType.SEMANTIC,
            "procedural": MemoryType.PROCEDURAL,
            "project": MemoryType.PROJECT,
        }

        mem_type = memory_type_map.get(memory_type.lower(), MemoryType.SEMANTIC)

        entry = MemoryEntry(
            project_id=target_project,
            content=content,
            memory_type=mem_type,
            metadata={"title": title} if title else {},
        )
        entry_id = run_async(framework._memory_store.store(entry))

        console.print(f"[bold green]Memory entry created:[/] {entry_id}")

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


# =============================================================================
# Session Commands
# =============================================================================


session_app = typer.Typer(help="Session management commands")
app.add_typer(session_app, name="session")


@session_app.command("new")
def new_session(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
):
    """
    Create a new session.

    Examples:
        palace session new
        palace session new --project my-api
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    try:
        framework = get_framework()

        session = run_async(
            framework._context_manager.create_session(
                project_id=target_project,
            )
        )

        console.print(
            Panel.fit(
                f"[bold green]Session created![/]\n\n"
                f"Session ID: {session.session_id}\n"
                f"Project: {target_project}",
                title="[bold]New Session[/]",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


@session_app.command("history")
def session_history(
    session_id: str = typer.Argument(..., help="Session ID"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Number of messages"),
):
    """
    Show session history.

    Examples:
        palace session history abc-123
        palace session history abc-123 --limit 50
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    try:
        framework = get_framework()

        history = run_async(
            framework._context_manager.get_session_history(
                project_id=target_project,
                session_id=session_id,
                limit=limit,
            )
        )

        if not history:
            console.print("[yellow]No messages found in this session.[/]")
            return

        console.print(f"\n[bold]Session: {session_id}[/]\n")

        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            role_style = {
                "user": "blue",
                "assistant": "green",
                "system": "yellow",
            }.get(role, "white")

            console.print(f"[bold {role_style}]{role}:[/] {content[:200]}")

    except Exception as e:
        console.print(f"[bold red]Error:[/] {e}")
        raise typer.Exit(1)


# =============================================================================
# Configuration Commands
# =============================================================================


@app.command("config")
def show_config(
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """
    Show current configuration.

    Displays the framework configuration including model assignments,
    memory settings, and API configuration.

    Examples:
        palace config
        palace config --json
    """
    settings = get_settings()

    if json_output:
        config_dict = {
            "ollama": {
                "base_url": settings.ollama.base_url,
                "timeout": settings.ollama.timeout,
            },
            "models": {
                "orchestrator": settings.model.orchestrator,
                "backend": settings.model.backend,
                "frontend": settings.model.frontend,
                "devops": settings.model.devops,
                "dba": settings.model.dba,
                "qa": settings.model.qa,
                "reviewer": settings.model.reviewer,
                "embedding": settings.model.embedding,
            },
            "memory": {
                "store_type": settings.memory.store_type,
                "collection_name": settings.memory.collection_name,
            },
            "api": {
                "host": settings.api.host,
                "port": settings.api.port,
                "debug": settings.api.debug,
            },
            "cli": {
                "default_project": settings.cli.default_project,
                "output_format": settings.cli.output_format,
            },
        }
        console.print_json(json.dumps(config_dict, indent=2))
    else:
        table = Table(title="Palace Configuration")
        table.add_column("Section", style="cyan")
        table.add_column("Key", style="yellow")
        table.add_column("Value", style="green")

        table.add_row("Ollama", "base_url", settings.ollama.base_url)
        table.add_row("Ollama", "timeout", str(settings.ollama.timeout))

        table.add_row("Models", "orchestrator", settings.model.orchestrator)
        table.add_row("Models", "backend", settings.model.backend)
        table.add_row("Models", "frontend", settings.model.frontend)
        table.add_row("Models", "devops", settings.model.devops)
        table.add_row("Models", "dba", settings.model.dba)
        table.add_row("Models", "qa", settings.model.qa)
        table.add_row("Models", "reviewer", settings.model.reviewer)
        table.add_row("Models", "embedding", settings.model.embedding)

        table.add_row("Memory", "store_type", settings.memory.store_type)
        table.add_row("Memory", "collection", settings.memory.collection_name)

        table.add_row("API", "host", settings.api.host)
        table.add_row("API", "port", str(settings.api.port))

        table.add_row("CLI", "default_project", settings.cli.default_project)

        console.print(table)


# =============================================================================
# Attach Command
# =============================================================================


@app.command("attach")
def attach_project(
    project_id: str = typer.Argument(..., help="Project ID to attach to"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path to project directory"),
):
    """
    Attach to an existing project and load its context.

    Loads the project's AI context files and makes it the active project.

    Examples:
        palace attach my-api
        palace attach my-api --path /path/to/project
    """
    console.print(f"[bold blue]Attaching to project:[/] {project_id}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading project context...", total=None)

        try:
            framework = get_framework()

            # Set the project as active using context_manager
            framework._context_manager.set_active_project(project_id)
            progress.update(task, description="Project set as active")

            # Attempt to load project context files from /ai_context/
            context_files_loaded = []
            if path:
                project_path = Path(path)
            else:
                project_path = Path.cwd()

            try:
                loader = ProjectLoader(project_path=project_path)
                _ = run_async(loader.load())
                if loader.is_loaded:
                    context_files_loaded = loader.loaded_files
                    progress.update(
                        task,
                        description=f"Loaded {len(context_files_loaded)} context files",
                    )
            except Exception:
                progress.update(task, description="Project attached (no context files found)")

            # Build success message
            success_msg = (
                f"[bold green]Attached to project '{project_id}'![/]\n\nProject ID: {project_id}\n"
            )
            if context_files_loaded:
                success_msg += f"Context files loaded: {', '.join(context_files_loaded)}\n"
            success_msg += "\nUse 'palace run' to execute tasks."

            console.print(
                Panel.fit(
                    success_msg,
                    title="[bold]Palace Project[/]",
                    border_style="green",
                )
            )

        except Exception as e:
            progress.stop()
            console.print(f"[bold red]Error:[/] {e}")
            raise typer.Exit(1)


# =============================================================================
# Interactive Mode
# =============================================================================


@app.command("interactive")
def interactive_mode(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID"),
):
    """
    Start interactive chat mode.

    Opens an interactive REPL for continuous interaction with the framework.

    Examples:
        palace interactive
        palace interactive --project my-api
    """
    settings = get_settings()
    target_project = project or settings.cli.default_project

    framework = get_framework()
    session_id = None
    context_files_loaded = []

    # Load project context at startup
    try:
        loader = ProjectLoader(project_path=Path.cwd())
        _ = run_async(loader.load())
        if loader.is_loaded:
            context_files_loaded = loader.loaded_files
    except Exception:
        pass

    # Build startup message with context info
    startup_msg = f"[bold]Palace Interactive Mode[/]\n\nProject: {target_project}\n"
    if context_files_loaded:
        startup_msg += f"Context files: {', '.join(context_files_loaded)}\n"
    startup_msg += (
        "Type your tasks and press Enter to execute.\n"
        "Type 'exit' or 'quit' to exit.\n"
        "Type 'help' for available commands."
    )
    console.print(Panel.fit(startup_msg, border_style="blue"))

    # Create a new session using context_manager directly
    try:
        session = run_async(
            framework._context_manager.create_session(
                project_id=target_project,
            )
        )
        session_id = str(session.session_id)
    except Exception:
        pass

    while True:
        try:
            console.print()
            user_input = console.input("[bold cyan]palace>[/] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Goodbye![/]")
                break

            if user_input.lower() == "help":
                console.print(
                    """
[bold]Available Commands:[/]
  <task>      - Execute a task
  agents      - List available agents
  status      - Show project status
  config      - Show configuration
  clear       - Clear screen
  help        - Show this help
  exit/quit   - Exit interactive mode
"""
                )
                continue

            if user_input.lower() == "clear":
                console.clear()
                continue

            if user_input.lower() == "agents":
                list_agents()
                continue

            if user_input.lower() == "status":
                project_status(project_id=target_project)
                continue

            if user_input.lower() == "config":
                show_config()
                continue

            # Execute task
            result = run_async(
                framework.execute(
                    task=user_input,
                    project_id=target_project,
                    session_id=session_id,
                )
            )

            console.print()
            console.print(
                Panel(
                    result.result[:1000] + "..." if len(result.result) > 1000 else result.result,
                    title=f"[bold]{result.agent_used}[/]",
                    border_style="green" if result.status == "success" else "red",
                )
            )

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Type 'exit' to quit.[/]")
            continue
        except Exception as e:
            console.print(f"[bold red]Error:[/] {e}")


# =============================================================================
# Version and Help
# =============================================================================


@app.command("version")
def show_version():
    """Show Palace version."""
    from palace import __version__

    console.print(f"Palace Framework v{__version__}")


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    app()
