"""
Palace Framework - Tools Module

This module provides shared tools and utilities that agents can use
to interact with the system, execute commands, and perform operations.

Tools are organized by category:
    - shell: Command execution (shell commands, scripts)
    - file: File operations (read, write, edit, delete)
    - git: Git operations (commit, branch, merge, diff)
    - code: Code analysis (linter, formatter, test runner)
    - web: Web operations (HTTP client, API calls)
    - data: Data processing (JSON, YAML, CSV, etc.)

Each tool implements the ToolBase interface and can be registered
with agents that need them.

Usage:
    from palace.tools import ShellTool, FileTool, GitTool

    # Create tools
    shell = ShellTool()
    file_tool = FileTool()

    # Register with agent
    agent.register_tool(shell)
    agent.register_tool(file_tool)

    # Execute tools
    result = await shell.execute(command="ls -la")
"""

from palace.tools.base import (
    ToolBase,
    ToolConfig,
    ToolRegistry,
    ToolResult,
    register_tool,
)
from palace.tools.code_tools import FormatterTool, LinterTool, TestRunnerTool
from palace.tools.data_tools import CSVTool, JSONTool, YAMLTool
from palace.tools.file_tools import FileDeleteTool, FileReadTool, FileWriteTool
from palace.tools.git_tools import GitCommitTool, GitDiffTool, GitTool
from palace.tools.shell_tools import ScriptRunnerTool, ShellTool
from palace.tools.web_tools import APIClientTool, HTTPClientTool

__all__ = [
    # Base classes
    "ToolBase",
    "ToolConfig",
    "ToolRegistry",
    "ToolResult",
    "register_tool",
    # File tools
    "FileReadTool",
    "FileWriteTool",
    "FileDeleteTool",
    # Shell tools
    "ShellTool",
    "ScriptRunnerTool",
    # Git tools
    "GitTool",
    "GitDiffTool",
    "GitCommitTool",
    # Code tools
    "LinterTool",
    "TestRunnerTool",
    "FormatterTool",
    # Web tools
    "HTTPClientTool",
    "APIClientTool",
    # Data tools
    "JSONTool",
    "YAMLTool",
    "CSVTool",
]
