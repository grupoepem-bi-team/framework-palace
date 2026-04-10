"""
Palace Framework - Clases Base de Pipelines

Este módulo define las clases base abstractas y los tipos de datos fundamentales
para el sistema de pipelines del framework. Proporciona la infraestructura sobre
la cual se construyen todos los flujos de trabajo complejos que involucran
múltiples agentes.

Clases principales:
    - PipelineStatus: Estados posibles de un pipeline
    - StepStatus: Estados posibles de un paso
    - StepResult: Resultado de la ejecución de un paso
    - PipelineResult: Resultado de la ejecución de un pipeline completo
    - PipelineContext: Contexto compartido entre los pasos de un pipeline
    - PipelineStep: Clase base abstracta para pasos de pipeline
    - Pipeline: Clase base abstracta para pipelines

Arquitectura:
    ┌─────────────────────────────────────────────────────┐
    │                     Pipeline                         │
    │  ┌───────────────────────────────────────────────┐  │
    │  │              PipelineContext                   │  │
    │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │  │
    │  │  │ Step 1  │ │ Step 2  │ │ Step 3  │        │  │
    │  │  └─────────┘ └─────────┘ └─────────┘        │  │
    │  │       │           │           │               │  │
    │  │       ▼           ▼           ▼               │  │
    │  │  StepResult  StepResult  StepResult           │  │
    │  └───────────────────────────────────────────────┘  │
    │                     │                                │
    │                     ▼                                │
    │               PipelineResult                        │
    └─────────────────────────────────────────────────────┘

Uso:
    from palace.pipelines.base import Pipeline, PipelineStep, PipelineContext

    class MiPaso(PipelineStep):
        async def execute(self, context: PipelineContext) -> StepResult:
            # Lógica del paso
            return StepResult(
                step_id=self.step_id,
                status=StepStatus.COMPLETED,
                result="Ejecutado exitosamente"
            )

        def can_execute(self, context: PipelineContext) -> bool:
            return True

    class MiPipeline(Pipeline):
        def build_steps(self) -> List[PipelineStep]:
            return [MiPaso(config=step_config)]

        def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
            return PipelineContext(
                pipeline_id=self.pipeline_id,
                project_id=project_id,
                task_description=task_description,
            )
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog

from palace.pipelines.types import PipelineConfig, PipelineType, StepConfig, StepType


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""

    PENDING = "pending"
    """Pipeline is waiting to start."""

    RUNNING = "running"
    """Pipeline is executing."""

    PAUSED = "paused"
    """Pipeline is paused (waiting for approval)."""

    COMPLETED = "completed"
    """Pipeline finished successfully."""

    FAILED = "failed"
    """Pipeline failed."""

    CANCELLED = "cancelled"
    """Pipeline was cancelled."""


class StepStatus(str, Enum):
    """Status of a pipeline step execution."""

    PENDING = "pending"
    """Step waiting to execute."""

    RUNNING = "running"
    """Step is executing."""

    COMPLETED = "completed"
    """Step completed successfully."""

    FAILED = "failed"
    """Step failed."""

    SKIPPED = "skipped"
    """Step was skipped (condition not met)."""

    WAITING_APPROVAL = "waiting_approval"
    """Step waiting for human approval."""


@dataclass
class StepResult:
    """Result of a single pipeline step execution."""

    step_id: str
    status: StepStatus
    result: str = ""
    """Output content."""

    artifacts: Dict[str, Any] = field(default_factory=dict)
    """Generated artifacts."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Step metadata."""

    error: Optional[str] = None
    """Error message if failed."""

    execution_time_seconds: float = 0.0
    tokens_used: int = 0
    agent_used: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution."""

    pipeline_id: str
    status: PipelineStatus
    step_results: List[StepResult] = field(default_factory=list)

    final_result: str = ""
    """Final output."""

    artifacts: Dict[str, Any] = field(default_factory=dict)
    """All artifacts."""

    errors: List[str] = field(default_factory=list)
    """Errors encountered."""

    total_execution_time: float = 0.0
    total_tokens_used: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineContext:
    """Shared context for a pipeline execution.

    Holds the state that is passed between steps and accumulated
    throughout the pipeline execution.
    """

    pipeline_id: str
    project_id: str
    session_id: Optional[str] = None
    task_description: str = ""
    """Original task description."""

    variables: Dict[str, Any] = field(default_factory=dict)
    """Pipeline variables (shared state between steps)."""

    step_outputs: Dict[str, StepResult] = field(default_factory=dict)
    """Outputs by step_id."""

    memory_entries: List[str] = field(default_factory=list)
    """IDs of memory entries created."""

    config: Optional[PipelineConfig] = None


class PipelineStep(ABC):
    """Abstract base class for pipeline steps."""

    def __init__(self, config: StepConfig):
        self.config = config
        self.step_id = config.step_id
        self.name = config.name
        self.step_type = config.step_type
        self._status = StepStatus.PENDING
        self._result: Optional[StepResult] = None
        self._logger = structlog.get_logger()

    @property
    def status(self) -> StepStatus:
        """Current status of the step."""
        return self._status

    @property
    def result(self) -> Optional[StepResult]:
        """Result of the step execution, if available."""
        return self._result

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StepResult:
        """Execute the step with the given context."""
        pass

    @abstractmethod
    def can_execute(self, context: PipelineContext) -> bool:
        """Check if this step can execute given the current context."""
        pass

    def get_task_description(self, context: PipelineContext) -> str:
        """Build task description from template and context variables."""
        template = self.config.task_template
        try:
            return template.format(**context.variables)
        except (KeyError, IndexError):
            return template


class Pipeline(ABC):
    """Abstract base class for pipelines."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.pipeline_id = config.pipeline_id
        self.name = config.name
        self.pipeline_type = config.pipeline_type
        self._status = PipelineStatus.PENDING
        self._steps: List[PipelineStep] = []
        self._context: Optional[PipelineContext] = None
        self._result: Optional[PipelineResult] = None
        self._logger = structlog.get_logger()

    @property
    def status(self) -> PipelineStatus:
        """Current status of the pipeline."""
        return self._status

    @property
    def steps(self) -> List[PipelineStep]:
        """List of pipeline steps."""
        return self._steps

    @abstractmethod
    def build_steps(self) -> List[PipelineStep]:
        """Build the pipeline steps based on configuration."""
        pass

    @abstractmethod
    def get_initial_context(self, task_description: str, project_id: str) -> PipelineContext:
        """Create initial pipeline context."""
        pass

    async def validate(self) -> bool:
        """Validate pipeline configuration before execution."""
        if not self._steps:
            self._logger.warning("pipeline_has_no_steps", pipeline_id=self.pipeline_id)
            return False
        return True

    def get_step_by_id(self, step_id: str) -> Optional[PipelineStep]:
        """Find a step by its ID."""
        for step in self._steps:
            if step.step_id == step_id:
                return step
        return None
