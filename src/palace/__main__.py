"""
Palace Framework - Main Entry Point

This module provides the main entry point for running the Palace Framework.
It can be executed directly or via `python -m palace`.

Usage:
    python -m palace [options]
    python -m palace api --host 0.0.0.0 --port 8000
    python -m palace cli --help

The entry point supports:
    - Starting the REST API server
    - Running the CLI interface
    - Development mode with auto-reload
"""

import asyncio
import sys
from typing import Optional

import structlog
import uvicorn

from palace.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


def run_api(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
    workers: int = 1,
) -> None:
    """
    Start the REST API server.

    Args:
        host: Host to bind to (default from settings)
        port: Port to bind to (default from settings)
        reload: Enable auto-reload for development
        workers: Number of worker processes
    """
    host = host or settings.api.host
    port = port or settings.api.port

    logger.info(
        "starting_api_server",
        host=host,
        port=port,
        reload=reload,
        workers=workers,
        environment=settings.environment,
    )

    uvicorn.run(
        "palace.api.main:app",
        host=host,
        port=port,
        reload=reload or settings.api.debug,
        workers=workers,
        log_level=settings.logging.level.lower(),
        access_log=True,
    )


def run_cli() -> None:
    """
    Start the CLI interface.

    This imports and runs the Typer CLI application.
    """
    from palace.cli.main import app

    app()


def run_worker() -> None:
    """
    Start a background worker for task processing.

    This is useful for distributed deployments where the API
    and task processing are separated.
    """
    logger.info("starting_background_worker")

    async def worker_loop() -> None:
        """Main worker loop for processing tasks."""
        from palace.core.framework import PalaceFramework

        framework = PalaceFramework(settings)
        await framework.initialize()

        try:
            while True:
                # Process pending tasks
                # TODO: Implement task queue processing
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("worker_shutdown_requested")
        finally:
            await framework.shutdown()

    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("worker_interrupted")


def print_version() -> None:
    """Print the framework version."""
    from palace import __version__

    print(f"Palace Framework v{__version__}")


def print_help() -> None:
    """Print help information."""
    help_text = """
Palace Framework - Multi-Agent Intelligent Software Development System

Usage:
    python -m palace <command> [options]

Commands:
    api       Start the REST API server
    cli       Start the CLI interface
    worker    Start a background worker
    version   Print the version
    help      Print this help message

API Options:
    --host        Host to bind to (default: 0.0.0.0)
    --port        Port to bind to (default: 8000)
    --reload      Enable auto-reload for development
    --workers     Number of worker processes (default: 1)

Examples:
    # Start API server
    python -m palace api --port 8080

    # Start in development mode with auto-reload
    python -m palace api --reload

    # Run CLI
    python -m palace cli

    # Start background worker
    python -m palace worker

Environment Variables:
    See .env.example for all available configuration options.

Documentation:
    https://palace-framework.readthedocs.io

Repository:
    https://github.com/palace-framework/palace
"""
    print(help_text)


def main() -> None:
    """
    Main entry point for the Palace Framework.

    Parses command-line arguments and dispatches to the appropriate
    subcommand (api, cli, worker, etc.).
    """
    # Parse arguments
    args = sys.argv[1:]

    if not args:
        print_help()
        sys.exit(0)

    command = args[0].lower()
    remaining_args = args[1:]

    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
            if settings.logging.format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    try:
        if command == "api":
            # Parse API options
            host = None
            port = None
            reload = False
            workers = 1

            i = 0
            while i < len(remaining_args):
                arg = remaining_args[i]
                if arg == "--host" and i + 1 < len(remaining_args):
                    host = remaining_args[i + 1]
                    i += 2
                elif arg == "--port" and i + 1 < len(remaining_args):
                    port = int(remaining_args[i + 1])
                    i += 2
                elif arg == "--reload":
                    reload = True
                    i += 1
                elif arg == "--workers" and i + 1 < len(remaining_args):
                    workers = int(remaining_args[i + 1])
                    i += 2
                else:
                    i += 1

            run_api(host=host, port=port, reload=reload, workers=workers)

        elif command == "cli":
            # Run CLI
            run_cli()

        elif command == "worker":
            # Run background worker
            run_worker()

        elif command == "version":
            # Print version
            print_version()

        elif command in ("help", "--help", "-h"):
            # Print help
            print_help()

        else:
            # Unknown command
            print(f"Unknown command: {command}")
            print("Run 'python -m palace help' for usage information.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("shutdown_requested")
        sys.exit(0)

    except Exception as e:
        logger.exception("fatal_error", error=str(e))
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
