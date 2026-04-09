"""
Palace Framework - Pipelines Module

This module provides workflow orchestration for complex multi-agent tasks.
Pipelines define sequences of operations that involve multiple agents
working together to accomplish a larger goal.

Pipeline Types:
    - Sequential: Steps executed in order, each step's output feeds the next
    - Parallel: Multiple steps executed concurrently
    - Conditional: Steps executed based on conditions
    - Recursive: Steps that loop until a condition is met

Available Pipelines:
    - FeatureDevelopmentPipeline: Full feature implementation (backend + frontend + tests)
    - CodeReviewPipeline: Code review and quality checks
    - DeploymentPipeline: CI/CD and deployment automation
    - DatabaseMigrationPipeline: Database schema changes
    - RefactoringPipeline: Code refactoring with safety checks
    - DocumentationPipeline: Documentation generation

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                    PipelineExecutor                       │
    │  ┌─────────────────────────────────────────────────┐    │
    │  │                   Pipeline                        │    │
    │  │  ┌──────────┐   ┌──────────┐   ┌──────────┐     │    │
    │  │  │  Step 1  │──▶│  Step 2  │──▶│  Step 3  │     │    │
    │  │  └──────────┘   └──────────┘   └──────────┘     │    │
    │  │       │              │              │            │    │
    │  │       ▼              ▼              ▼            │    │
    │  │  [Backend]      [Frontend]       [QA]          │    │
    │  └─────────────────────────────────────────────────┘    │
    └─────────────────────────────────────────────────────────┘

Usage:
    from palace.pipelines import FeatureDevelopmentPipeline, PipelineExecutor

    # Create and execute a pipeline
    pipeline = FeatureDevelopmentPipeline(
        project_id="my-project",
        feature="User authentication"
    )

    executor = PipelineExecutor()
    result = await executor.execute(pipeline)
"""

# Base classes
from palace.pipelines.base import (
    Pipeline,
    PipelineContext,
    PipelineResult,
    PipelineStatus,
    PipelineStep,
    StepResult,
    StepStatus,
)
from palace.pipelines.code_review import CodeReviewPipeline
from palace.pipelines.database_migration import DatabaseMigrationPipeline
from palace.pipelines.deployment import DeploymentPipeline
from palace.pipelines.documentation import DocumentationPipeline

# Executor
from palace.pipelines.executor import PipelineExecutor, get_executor

# Built-in pipelines
from palace.pipelines.feature_development import FeatureDevelopmentPipeline
from palace.pipelines.refactoring import RefactoringPipeline

# Types
from palace.pipelines.types import (
    PipelineConfig,
    PipelineDefinition,
    PipelineType,
    StepConfig,
    StepDefinition,
    StepType,
)

__all__ = [
    # Base classes
    "Pipeline",
    "PipelineStep",
    "PipelineContext",
    "PipelineResult",
    "PipelineStatus",
    "StepResult",
    "StepStatus",
    # Executor
    "PipelineExecutor",
    "get_executor",
    # Built-in pipelines
    "FeatureDevelopmentPipeline",
    "CodeReviewPipeline",
    "DeploymentPipeline",
    "DatabaseMigrationPipeline",
    "RefactoringPipeline",
    "DocumentationPipeline",
    # Types
    "PipelineType",
    "PipelineConfig",
    "PipelineDefinition",
    "StepType",
    "StepConfig",
    "StepDefinition",
]
