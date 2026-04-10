"""
Palace Framework - Command Line Interface Module

This module provides the CLI for interacting with the Palace framework.
It offers commands for:

- Project management: init, status, list
- Task execution: run, cancel, status
- Memory management: store, query, clear
- Session management: session, history
- Agent interaction: agents, info

The CLI is built with Typer and provides:
- Interactive mode for conversations
- Batch mode for automation
- Colorful output with Rich
- Progress tracking and spinners
- Configuration management

Usage:
    palace init my-project
    palace run "Create a REST endpoint for user management"
    palace status --project my-project
    palace memory query "architecture decisions"
    palace agents list

Architecture:
    - main.py: CLI entry point and command definitions
    - commands/: Individual command implementations
    - utils/: Helper utilities for CLI
    - config/: CLI configuration management
"""

from palace.cli.main import app

__all__ = [
    "app",
]
