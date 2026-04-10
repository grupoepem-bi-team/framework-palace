"""
Palace Framework - Tipos de Pipelines

Este módulo define los tipos, enumeraciones y estructuras de datos
utilizados en el sistema de pipelines del framework. Estos tipos
proporcionan la base para la configuración y definición de flujos
de trabajo complejos que involucran múltiples agentes.

Tipos principales:
    - StepType: Tipos de pasos disponibles en un pipeline
    - PipelineType: Tipos de pipelines predefinidos
    - StepConfig: Configuración de un paso individual
    - StepDefinition: Definición completa de un paso
    - PipelineConfig: Configuración de un pipeline
    - PipelineDefinition: Definición completa de un pipeline

Arquitectura:
    ┌────────────────────────────────────────────────────┐
    │               PipelineDefinition                    │
    │  ┌──────────────────────────────────────────────┐  │
    │  │              PipelineConfig                   │  │
    │  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │  │
    │  │  │ Step 1  │ │ Step 2  │ │ Step 3  │       │  │
    │  │  └─────────┘ └─────────┘ └─────────┘       │  │
    │  │       │           │           │              │  │
    │  │       ▼           ▼           ▼              │  │
    │  │  [AGENT]    [CONDITIONAL] [PARALLEL]        │  │
    │  └──────────────────────────────────────────────┘  │
    └────────────────────────────────────────────────────┘

Uso:
    from palace.pipelines.types import PipelineConfig, StepConfig

    config = PipelineConfig(
        pipeline_id="feat-001",
        name="Mi Pipeline",
        pipeline_type=PipelineType.FEATURE_DEVELOPMENT,
        project_id="my-project",
        steps=[
            StepConfig(
                step_id="step-1",
                name="Primer paso",
                step_type=StepType.AGENT_TASK,
                agent_role="backend",
            )
        ],
    )
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """
    Tipos de pasos disponibles en un pipeline.

    Cada tipo define un comportamiento específico para la ejecución
    del paso dentro del flujo del pipeline.
    """

    AGENT_TASK = "agent_task"
    """Paso que delega la ejecución a un agente especializado."""

    CONDITIONAL = "conditional"
    """Paso que ejecuta condicionalmente basado en una expresión."""

    PARALLEL = "parallel"
    """Paso que ejecuta sub-pasos en paralelo."""

    VALIDATION = "validation"
    """Paso que valida el resultado de pasos anteriores."""

    TRANSFORM = "transform"
    """Paso que transforma los datos de entrada en un nuevo formato."""

    HUMAN_APPROVAL = "human_approval"
    """Paso que requiere aprobación humana antes de continuar."""


class PipelineType(str, Enum):
    """
    Tipos de pipelines predefinidos en el framework.

    Cada tipo define un flujo de trabajo específico con pasos
    y configuraciones optimizadas para el caso de uso correspondiente.
    """

    FEATURE_DEVELOPMENT = "feature_development"
    """Pipeline para implementación completa de una funcionalidad."""

    CODE_REVIEW = "code_review"
    """Pipeline para flujo de revisión de código."""

    DEPLOYMENT = "deployment"
    """Pipeline para flujo de despliegue."""

    DATABASE_MIGRATION = "database_migration"
    """Pipeline para flujo de migración de base de datos."""

    REFACTORING = "refactoring"
    """Pipeline para flujo de refactorización de código."""

    DOCUMENTATION = "documentation"
    """Pipeline para generación de documentación."""

    BUG_FIX = "bug_fix"
    """Pipeline para flujo de corrección de errores."""

    CUSTOM = "custom"
    """Pipeline personalizado con configuración arbitraria."""


class StepConfig(BaseModel):
    """
    Configuración de un paso individual dentro de un pipeline.

    Atributos:
        step_id: Identificador único del paso dentro del pipeline.
        name: Nombre descriptivo del paso.
        step_type: Tipo de paso que determina su comportamiento.
        agent_role: Rol del agente a utilizar (para pasos de tipo AGENT_TASK).
        task_template: Plantilla para la descripción de la tarea.
        condition: Expresión condicional (para pasos de tipo CONDITIONAL).
        depends_on: Lista de IDs de pasos de los que depende este paso.
        retry_count: Número de reintentos en caso de fallo.
        timeout_seconds: Tiempo máximo de ejecución del paso en segundos.
        parallel_steps: Sub-pasos a ejecutar en paralelo (para tipo PARALLEL).
        validation_criteria: Criterio de validación (para tipo VALIDATION).
        metadata: Metadatos adicionales del paso.
    """

    step_id: str
    name: str
    step_type: StepType
    agent_role: Optional[str] = None
    task_template: str = ""
    condition: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    retry_count: int = 0
    timeout_seconds: int = 300
    parallel_steps: List["StepConfig"] = Field(default_factory=list)
    validation_criteria: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StepDefinition(BaseModel):
    """
    Definición completa de un paso de pipeline.

    Combina la configuración del paso con su identificación y tipo,
    proporcionando una vista completa y autónoma del paso.

    Atributos:
        id: Identificador único del paso.
        name: Nombre descriptivo del paso.
        type: Tipo de paso que determina su comportamiento.
        config: Configuración detallada del paso.
    """

    id: str
    name: str
    type: StepType
    config: StepConfig


class PipelineConfig(BaseModel):
    """
    Configuración de un pipeline completo.

    Define todos los parámetros necesarios para la ejecución de un pipeline,
    incluyendo los pasos, tiempos de espera y comportamiento ante fallos.

    Atributos:
        pipeline_id: Identificador único del pipeline.
        name: Nombre descriptivo del pipeline.
        pipeline_type: Tipo de pipeline que determina el flujo base.
        description: Descripción del propósito del pipeline.
        project_id: Identificador del proyecto asociado.
        steps: Lista de configuraciones de pasos del pipeline.
        max_retries: Número máximo de reintentos para el pipeline.
        timeout_seconds: Tiempo máximo total de ejecución del pipeline en segundos.
        auto_approve: Indica si se aprueban automáticamente los pasos que requieren aprobación humana.
        stop_on_failure: Indica si se detiene el pipeline ante un fallo en un paso.
        save_intermediate_results: Indica si se guardan los resultados intermedios en memoria.
        metadata: Metadatos adicionales del pipeline.
    """

    pipeline_id: str
    name: str
    pipeline_type: PipelineType
    description: str = ""
    project_id: str
    steps: List[StepConfig] = Field(default_factory=list)
    max_retries: int = 3
    timeout_seconds: int = 3600
    auto_approve: bool = False
    stop_on_failure: bool = True
    save_intermediate_results: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PipelineDefinition(BaseModel):
    """
    Definición completa de un pipeline.

    Combina la configuración del pipeline con sus definiciones de pasos,
    proporcionando una vista completa y autónoma del flujo de trabajo.

    Atributos:
        id: Identificador único del pipeline.
        name: Nombre descriptivo del pipeline.
        type: Tipo de pipeline que determina el flujo base.
        description: Descripción del propósito del pipeline.
        steps: Lista de definiciones de pasos del pipeline.
        config: Configuración detallada del pipeline.
    """

    id: str
    name: str
    type: PipelineType
    description: str = ""
    steps: List[StepDefinition] = Field(default_factory=list)
    config: PipelineConfig


# Resolver referencias circulares en StepConfig
StepConfig.model_rebuild()
