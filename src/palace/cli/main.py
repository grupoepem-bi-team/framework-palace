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
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table

from palace.core.config import get_settings
from palace.core.framework import PalaceFramework

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
):
    """
    Initialize a new Palace project.

    Creates a new project with the specified configuration and
    initializes its context in the memory store.

    Examples:
        palace init my-api
        palace init my-app --backend fastapi --db postgresql
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

            # Create project
            context = run_async(
                framework._orchestrator._context_manager.create_project(
                    project_id=name.lower().replace(" ", "-"),
                    name=name,
                    description=description,
                    config=config,
                )
            )

            progress.update(task, description="Project created!")

            console.print(
                Panel.fit(
                    f"[bold green]Project '{name}' created successfully![/]\n\n"
                    f"Project ID: {context.config.project_id}\n"
                    f"Use 'palace run' to execute tasks.",
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

        # Agent info mapping
        agent_info = {
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

        if json_output:
            console.print_json(json.dumps({"agents": agents}, indent=2))
        else:
            table = Table(title="Available Agents")
            table.add_column("Agent", style="cyan")
            table.add_column("Model", style="green")
            table.add_column("Description", style="white")
            table.add_column("Capabilities", style="yellow")

            for agent_name in agents:
                info = agent_info.get(agent_name, {})
                table.add_row(
                    agent_name,
                    info.get("model", "unknown"),
                    info.get("description", ""),
                    ", ".join(info.get("capabilities", [])[:2]),
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
    agent_data = {
        "backend": {
            "model": "qwen3-coder-next",
            "description": "Backend development specialist for APIs, services, and business logic",
            "capabilities": [
                "backend_development",
                "fullstack_development",
                "testing",
                "documentation",
            ],
            "tools": ["shell", "file_read", "file_write", "linter", "test_runner", "http_client"],
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
            "tools_detail": ["GitHub Actions", "GitLab CI", "Docker", "Kubernetes", "Terraform"],
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

    if agent_name not in agent_data:
        console.print(f"[bold red]Error:[/] Agent '{agent_name}' not found")
        console.print(f"Available agents: {', '.join(agent_data.keys())}")
        raise typer.Exit(1)

    info = agent_data[agent_name]

    console.print(Panel(f"[bold]{agent_name.upper()}[/] Agent", border_style="cyan"))
    console.print(f"\n[bold]Model:[/] {info['model']}")
    console.print(f"[bold]Description:[/] {info['description']}")

    console.print(f"\n[bold]Capabilities:[/]")
    for cap in info["capabilities"]:
        console.print(f"  • {cap}")

    console.print(f"\n[bold]Tools:[/]")
    for tool in info["tools"]:
        console.print(f"  • {tool}")


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

        # Query memory
        results = run_async(
            framework._orchestrator._memory_store.retrieve_context(
                project_id=target_project,
                query=query,
                top_k=top_k,
            )
        )

        if json_output:
            console.print_json(json.dumps({"results": results}, indent=2))
        else:
            if not results:
                console.print("[yellow]No results found.[/]")
                return

            console.print(f"\n[bold]Found {len(results)} results:[/]\n")

            for i, result in enumerate(results, 1):
                score = result.get("score", 0)
                content = result.get("content", "")[:200]

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

        entry_id = run_async(
            framework._orchestrator._memory_store.store_context(
                project_id=target_project,
                content=content,
                memory_type=memory_type,
                metadata={"title": title} if title else {},
            )
        )

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
            framework._orchestrator._context_manager.create_session(
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
            framework._orchestrator._context_manager.get_session_history(
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
            timestamp = msg.get("timestamp", "")

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

    console.print(
        Panel.fit(
            "[bold]Palace Interactive Mode[/]\n\n"
            f"Project: {target_project}\n"
            "Type your tasks and press Enter to execute.\n"
            "Type 'exit' or 'quit' to exit.\n"
            "Type 'help' for available commands.",
            border_style="blue",
        )
    )

    framework = get_framework()
    session_id = None

    # Create a new session
    try:
        session = run_async(
            framework._orchestrator._context_manager.create_session(
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
