"""
Agente Orchestrator - Palace Framework

El Orchestrator es el coordinador central del sistema multi-agente. Sus responsabilidades son:
- Analizar y descomponer tareas complejas
- Enrutar tareas a agentes especializados según competencia
- Coordinar flujos de trabajo entre múltiples agentes
- Gestionar el estado de las tareas y proyectos
- Mantener contexto conversacional
- Resolver conflictos y manejar reintentos

Modelo asignado: qwen3.5

No debe:
- Generar código directamente
- Realizar tareas técnicas específicas
- Interactuar directamente con archivos o sistemas
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar

import structlog

from palace.agents.base import AgentBase, AgentContext, AgentResult, AgentStatus
from palace.llm import LLMClient
from palace.llm.models import AgentRole

if TYPE_CHECKING:
    from palace.context import ContextManager
    from palace.memory import MemoryStore

logger = structlog.get_logger()

T = TypeVar("T")


class TaskType(str, Enum):
    """Tipos de tareas que puede identificar el Orchestrator."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DATABASE = "database"
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    DESIGN = "design"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    UNKNOWN = "unknown"


class TaskComplexity(str, Enum):
    """Niveles de complejidad de tareas."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


@dataclass
class TaskAnalysis:
    """Resultado del análisis de una tarea."""

    task_type: TaskType
    complexity: TaskComplexity
    required_agents: List[AgentRole]
    suggested_workflow: str
    estimated_steps: int
    dependencies: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskPlan:
    """Plan de ejecución para una tarea compleja."""

    plan_id: str
    description: str
    steps: List[Dict[str, Any]]
    assigned_agents: Dict[str, AgentRole]
    estimated_time: int  # minutos
    priority: int = 5
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.utcnow)


class OrchestratorAgent(AgentBase):
    """
    Agente Orchestrator - Coordinador Central del Sistema.

    Este agente es el cerebro del sistema multi-agente. No ejecuta tareas
    técnicas directamente, sino que coordina y delega a los agentes
    especializados.

    Responsabilidades Principales:
    ─────────────────────────────────────────────────────────────────
    1. ANÁLISIS DE TAREAS
       - Interpretar la intención del usuario
       - Clasificar el tipo de tarea
       - Evaluar complejidad
       - Identificar riesgos

    2. PLANIFICACIÓN
       - Descomponer tareas complejas en subtareas
       - Definir secuencia de ejecución
       - Asignar agentes responsables
       - Estimar tiempos

    3. COORDINACIÓN
       - Enrutar tareas a agentes especializados
       - Gestionar dependencias entre tareas
       - Resolver conflictos
       - Monitorear progreso

    4. GESTIÓN DE CONTEXTO
       - Mantener historial conversacional
       - Recuperar contexto relevante de memoria
       - Actualizar estado del proyecto
       ─────────────────────────────────────────────────────────────────

    Modelo: qwen3.5 (optimizado para razonamiento y coordinación)

    Ejemplo de uso:
        >>> orchestrator = OrchestratorAgent(llm_client, context_manager, memory_store)
        >>> result = await orchestrator.run(
        ...     task="Crear un API REST para gestión de usuarios con tests",
        ...     context={"project_id": "my-project"}
        ... )
    """

    name: str = "orchestrator"
    role: AgentRole = AgentRole.ORCHESTRATOR
    description: str = (
        "Coordinador central del sistema multi-agente. "
        "Analiza tareas, planifica ejecución y delega a agentes especializados."
    )

    # System prompt específico del Orchestrator
    SYSTEM_PROMPT: str = """Eres el Orchestrator, el coordinador central de un sistema multi-agente especializado en desarrollo de software.

## Tu Rol

Tu función NO es ejecutar tareas técnicas directamente, sino COORDINAR y DELEGAR a los agentes especializados disponibles.

## Agentes Disponibles y sus Especialidades

| Agente | Rol | Especialidad |
|--------|-----|--------------|
| Backend | Desarrollo backend | APIs REST, lógica de negocio, ORM, microservicios |
| Frontend | Desarrollo frontend | UI/UX, componentes React/Vue, estado, estilos |
| DBA | Base de datos | SQL, migraciones, optimización, schema design |
| DevOps | CI/CD | Pipelines, automatización, despliegue |
| Infra | Infraestructura | Terraform, Kubernetes, Docker, cloud |
| QA | Calidad | Testing, cobertura, análisis de calidad |
| Designer | Diseño | UI/UX, accesibilidad, design systems |
| Reviewer | Revisión | Code review, arquitectura, mejores prácticas |

## Tu Proceso de Trabajo

### Paso 1: ANÁLISIS
Analiza la solicitud del usuario para identificar:
- Tipo de tarea (código, base de datos, infraestructura, etc.)
- Complejidad (simple, moderada, compleja, crítica)
- Agentes necesarios
- Dependencias entre tareas

### Paso 2: PLANIFICACIÓN
Si la tarea es compleja, créa un plan de ejecución con:
- Subtareas ordenadas
- Agentes asignados a cada subtarea
- Dependencias
- Estimación de tiempo

### Paso 3: DELEGACIÓN
Para cada subtarea, especifica:
- Agente responsable
- Prompt específico y detallado
- Contexto necesario
- Criterios de aceptación

## Formato de Respuesta

Responde SIEMPRE en formato estructurado:

```json
{
  "analysis": {
    "task_type": "tipo_de_tarea",
    "complexity": "nivel_de_complejidad",
    "required_agents": ["agente1", "agente2"],
    "risks": ["riesgo1", "riesgo2"]
  },
  "plan": {
    "description": "Descripción del plan general",
    "steps": [
      {
        "step": 1,
        "agent": "nombre_agente",
        "task": "descripción detallada de la subtarea",
        "context": "contexto específico necesario",
        "dependencies": [],
        "estimated_time_minutes": 15
      }
    ],
    "total_estimated_time": 45
  },
  "immediate_action": {
    "agent": "agente_a_ejecutar_primero",
    "prompt": "prompt detallado para el primer agente"
  }
}
```

## Reglas Importantes

1. NUNCA generes código tú mismo - siempre delega
2. Si una tarea es simple, delega directamente a un agente
3. Si una tarea es compleja, planifica primero antes de delegar
4. Considera dependencias: no puedes desplegar antes de tener código
5. Incluye contexto del proyecto en cada delegación
6. Sé específico en los prompts de delegación

## Ejemplos

### Tarea Simple:
Usuario: "Crea un endpoint REST para obtener usuarios"
→ Delega directamente a Backend con prompt específico

### Tarea Compleja:
Usuario: "Implementa un sistema de autenticación completo"
→ Planifica: Backend (API) → DBA (tablas) → Frontend (UI) → QA (tests)

Responde de forma concisa pero completa. Usa el formato JSON especificado."""

    # Prompt para análisis de tareas
    ANALYSIS_PROMPT_TEMPLATE: str = """Analiza la siguiente tarea y determina cómo debe ser procesada.

## Tarea del Usuario
{task}

## Contexto del Proyecto
{project_context}

## Contexto de Memoria Recuperado
{memory_context}

## Instrucciones
1. Identifica el tipo de tarea
2. Evalúa la complejidad
3. Determina qué agentes son necesarios
4. Identifica posibles riesgos
5. Si es compleja, crea un plan de ejecución

Responde en el formato JSON especificado en tu system prompt."""

    # Prompt para delegación
    DELEGATION_PROMPT_TEMPLATE: str = """Prepara la delegación de una subtarea a un agente especializado.

## Subtarea
{subtask}

## Agente Objetivo
{target_agent}

## Contexto del Proyecto
{project_context}

## Contexto de Sesión
{session_context}

## Resultados Previos (si aplica)
{previous_results}

## Instrucciones
Genera un prompt detallado y específico para el agente {target_agent}.
El prompt debe incluir:
- Objetivo claro
- Contexto técnico necesario
- Criterios de aceptación
- Restricciones o consideraciones

Responde con el prompt listo para enviar al agente."""

    def __init__(
        self,
        llm_client: LLMClient,
        context_manager: "ContextManager",
        memory_store: "MemoryStore",
    ):
        """
        Inicializa el agente Orchestrator.

        Args:
            llm_client: Cliente LLM para invocar modelos
            context_manager: Gestor de contexto del framework
            memory_store: Almacén de memoria vectorial
        """
        self._llm_client = llm_client
        self._context_manager = context_manager
        self._memory_store = memory_store
        self._status = AgentStatus.IDLE
        self._current_task_id: Optional[str] = None
        self._agent_registry: Dict[AgentRole, Any] = {}

        logger.info(
            "orchestrator_initialized",
            role=self.role.value,
            status=self._status.value,
        )

    def register_agent(self, agent: AgentBase) -> None:
        """
        Registra un agente especializado.

        Args:
            agent: Instancia del agente a registrar
        """
        self._agent_registry[agent.role] = agent
        logger.info(
            "agent_registered",
            orchestrator=self.name,
            agent=agent.name,
            role=agent.role.value,
        )

    def unregister_agent(self, role: AgentRole) -> bool:
        """
        Desregistra un agente.

        Args:
            role: Rol del agente a desregistrar

        Returns:
            True si se desregistró, False si no existía
        """
        if role in self._agent_registry:
            del self._agent_registry[role]
            logger.info("agent_unregistered", role=role.value)
            return True
        return False

    def get_registered_agents(self) -> List[AgentRole]:
        """
        Lista los agentes registrados.

        Returns:
            Lista de roles de agentes registrados
        """
        return list(self._agent_registry.keys())

    async def run(
        self,
        task: str,
        context: AgentContext,
    ) -> AgentResult:
        """
        Ejecuta una tarea de coordinación.

        Este es el método principal del Orchestrator. Analiza la tarea,
        planifica si es necesario, y delega a los agentes apropiados.

        Flujo:
        1. Recuperar contexto de memoria
        2. Analizar la tarea
        3. Determinar si es simple o compleja
        4. Si es simple → delegar directamente
        5. Si es compleja → planificar y ejecutar plan

        Args:
            task: Descripción de la tarea del usuario
            context: Contexto de ejecución (proyecto, sesión, etc.)

        Returns:
            AgentResult con el resultado de la coordinación
        """
        self._status = AgentStatus.BUSY
        start_time = datetime.utcnow()

        logger.info(
            "orchestrator_task_started",
            task_preview=task[:100],
            project_id=context.project_id,
        )

        try:
            # Paso 1: Recuperar contexto relevante
            memory_context = await self._retrieve_context(
                project_id=context.project_id,
                query=task,
            )

            # Paso 2: Analizar la tarea
            analysis = await self._analyze_task(
                task=task,
                project_context=context.to_dict(),
                memory_context=memory_context,
            )

            logger.info(
                "task_analyzed",
                task_type=analysis.task_type.value,
                complexity=analysis.complexity.value,
                required_agents=[a.value for a in analysis.required_agents],
            )

            # Paso 3: Ejecutar según complejidad
            if analysis.complexity in [TaskComplexity.SIMPLE, TaskComplexity.MODERATE]:
                # Tarea simple: delegar directamente
                result = await self._delegate_simple_task(
                    task=task,
                    analysis=analysis,
                    context=context,
                    memory_context=memory_context,
                )
            else:
                # Tarea compleja: planificar y ejecutar
                result = await self._execute_complex_task(
                    task=task,
                    analysis=analysis,
                    context=context,
                    memory_context=memory_context,
                )

            # Actualizar estado
            self._status = AgentStatus.IDLE

            logger.info(
                "orchestrator_task_completed",
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

            return result

        except Exception as e:
            self._status = AgentStatus.ERROR
            logger.exception(
                "orchestrator_task_failed",
                error=str(e),
            )

            return AgentResult(
                success=False,
                content="",
                error=f"Orchestration failed: {str(e)}",
                metadata={"task": task},
            )

    async def _retrieve_context(
        self,
        project_id: str,
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        Recupera contexto relevante de la memoria.

        Args:
            project_id: ID del proyecto
            query: Consulta para búsqueda semántica

        Returns:
            Lista de contexto recuperado
        """
        try:
            context = await self._memory_store.retrieve_context(
                project_id=project_id,
                query=query,
                top_k=5,
            )
            return context
        except Exception as e:
            logger.warning(
                "context_retrieval_failed",
                project_id=project_id,
                error=str(e),
            )
            return []

    async def _analyze_task(
        self,
        task: str,
        project_context: Dict[str, Any],
        memory_context: List[Dict[str, Any]],
    ) -> TaskAnalysis:
        """
        Analiza una tarea para determinar tipo, complejidad y agentes necesarios.

        Args:
            task: Descripción de la tarea
            project_context: Contexto del proyecto
            memory_context: Contexto recuperado de memoria

        Returns:
            TaskAnalysis con el análisis completo
        """
        # Preparar contexto para el LLM
        memory_text = "\n".join([f"- {ctx.get('content', '')[:200]}" for ctx in memory_context[:3]])

        prompt = self.ANALYSIS_PROMPT_TEMPLATE.format(
            task=task,
            project_context=str(project_context),
            memory_context=memory_text or "Sin contexto previo",
        )

        # Invocar LLM como orchestrator
        response = await self._llm_client.invoke(
            prompt=prompt,
            role="orchestrator",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,  # Baja temperatura para análisis más determinista
        )

        # Parsear respuesta
        analysis = self._parse_analysis_response(response.content)

        return analysis

    def _parse_analysis_response(self, response: str) -> TaskAnalysis:
        """
        Parsea la respuesta del LLM en un TaskAnalysis.

        Args:
            response: Respuesta del LLM

        Returns:
            TaskAnalysis estructurado
        """
        import json
        import re

        # Intentar extraer JSON de la respuesta
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                data = {}
        else:
            # Intentar parsear directamente
            try:
                data = json.loads(response)
            except json.JSONDecodeError:
                data = {}

        # Extraer análisis
        analysis_data = data.get("analysis", {})

        # Mapear tipo de tarea
        task_type_str = analysis_data.get("task_type", "unknown").lower()
        task_type = (
            TaskType(task_type_str)
            if task_type_str in [t.value for t in TaskType]
            else TaskType.UNKNOWN
        )

        # Mapear complejidad
        complexity_str = analysis_data.get("complexity", "moderate").lower()
        complexity = (
            TaskComplexity(complexity_str)
            if complexity_str in [c.value for c in TaskComplexity]
            else TaskComplexity.MODERATE
        )

        # Mapear agentes requeridos
        required_agents = []
        for agent_str in analysis_data.get("required_agents", []):
            try:
                required_agents.append(AgentRole(agent_str.lower()))
            except ValueError:
                continue

        # Si no se identificaron agentes, inferir por tipo de tarea
        if not required_agents:
            required_agents = self._infer_agents_from_task_type(task_type)

        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            required_agents=required_agents,
            suggested_workflow=data.get("plan", {}).get("description", ""),
            estimated_steps=len(data.get("plan", {}).get("steps", [])),
            risks=analysis_data.get("risks", []),
            metadata={"raw_response": data},
        )

    def _infer_agents_from_task_type(self, task_type: TaskType) -> List[AgentRole]:
        """
        Infiere agentes necesarios basado en el tipo de tarea.

        Args:
            task_type: Tipo de tarea identificado

        Returns:
            Lista de roles de agentes necesarios
        """
        mapping = {
            TaskType.CODE_GENERATION: [AgentRole.BACKEND, AgentRole.FRONTEND],
            TaskType.CODE_REVIEW: [AgentRole.REVIEWER],
            TaskType.DATABASE: [AgentRole.DBA],
            TaskType.INFRASTRUCTURE: [AgentRole.INFRA],
            TaskType.DEPLOYMENT: [AgentRole.DEVOPS],
            TaskType.TESTING: [AgentRole.QA],
            TaskType.DOCUMENTATION: [AgentRole.BACKEND],  # Backend puede generar docs
            TaskType.DESIGN: [AgentRole.DESIGNER],
            TaskType.ANALYSIS: [AgentRole.REVIEWER],
            TaskType.PLANNING: [AgentRole.ORCHESTRATOR],
            TaskType.UNKNOWN: [AgentRole.BACKEND],  # Default
        }
        return mapping.get(task_type, [AgentRole.BACKEND])

    async def _delegate_simple_task(
        self,
        task: str,
        analysis: TaskAnalysis,
        context: AgentContext,
        memory_context: List[Dict[str, Any]],
    ) -> AgentResult:
        """
        Delega una tarea simple a un agente especializado.

        Args:
            task: Tarea original
            analysis: Análisis de la tarea
            context: Contexto de ejecución
            memory_context: Contexto de memoria

        Returns:
            AgentResult con el resultado de la delegación
        """
        # Seleccionar el primer agente necesario
        target_role = analysis.required_agents[0]

        if target_role not in self._agent_registry:
            return AgentResult(
                success=False,
                content="",
                error=f"Agente {target_role.value} no está registrado",
                metadata={"analysis": analysis.to_dict()},
            )

        agent = self._agent_registry[target_role]

        # Preparar prompt de delegación
        delegation_prompt = self.DELEGATION_PROMPT_TEMPLATE.format(
            subtask=task,
            target_agent=target_role.value,
            project_context=str(context.to_dict()),
            session_context=str(context.session_id),
            previous_results="Ninguno",
        )

        # Obtener prompt delegado del LLM
        delegation_response = await self._llm_client.invoke(
            prompt=delegation_prompt,
            role="orchestrator",
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.5,
        )

        delegated_prompt = delegation_response.content

        # Ejecutar el agente especializado
        logger.info(
            "delegating_task",
            target_agent=target_role.value,
            original_task=task[:50],
        )

        # Crear contexto para el agente
        agent_context = AgentContext(
            project_id=context.project_id,
            session_id=context.session_id,
            memory_context=memory_context,
            additional_context={"delegated_by": "orchestrator"},
        )

        # Ejecutar
        result = await agent.run(
            task=delegated_prompt,
            context=agent_context,
        )

        # Guardar resultado en memoria
        await self._store_result(
            project_id=context.project_id,
            session_id=context.session_id,
            result=result,
            delegated_to=target_role.value,
        )

        return AgentResult(
            success=result.success,
            content=result.content,
            metadata={
                "delegated_to": target_role.value,
                "analysis": analysis.to_dict(),
                "agent_result": result.to_dict(),
            },
        )

    async def _execute_complex_task(
        self,
        task: str,
        analysis: TaskAnalysis,
        context: AgentContext,
        memory_context: List[Dict[str, Any]],
    ) -> AgentResult:
        """
        Ejecuta una tarea compleja mediante un plan multi-agente.

        Args:
            task: Tarea original
            analysis: Análisis de la tarea
            context: Contexto de ejecución
            memory_context: Contexto de memoria

        Returns:
            AgentResult con el resultado consolidado
        """
        logger.info(
            "executing_complex_task",
            required_agents=[a.value for a in analysis.required_agents],
            estimated_steps=analysis.estimated_steps,
        )

        # Crear plan de ejecución
        plan = await self._create_execution_plan(
            task=task,
            analysis=analysis,
            context=context,
        )

        results = []
        previous_results = []

        # Ejecutar cada paso del plan
        for step in plan.steps:
            agent_role = step.get("agent")
            subtask = step.get("task")

            if not agent_role or not subtask:
                continue

            # Verificar que el agente esté registrado
            if agent_role not in self._agent_registry:
                logger.warning(
                    "agent_not_registered",
                    agent=agent_role,
                    step=step.get("step"),
                )
                continue

            agent = self._agent_registry[agent_role]

            # Preparar contexto con resultados previos
            previous_context = "\n".join(
                [f"Resultado previo: {r[:200]}..." for r in previous_results]
            )

            # Preparar prompt de delegación
            delegation_prompt = self.DELEGATION_PROMPT_TEMPLATE.format(
                subtask=subtask,
                target_agent=agent_role,
                project_context=str(context.to_dict()),
                session_context=str(context.session_id),
                previous_results=previous_context or "Sin resultados previos",
            )

            # Obtener prompt delegado
            delegation_response = await self._llm_client.invoke(
                prompt=delegation_prompt,
                role="orchestrator",
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.5,
            )

            delegated_prompt = delegation_response.content

            # Ejecutar agente
            agent_context = AgentContext(
                project_id=context.project_id,
                session_id=context.session_id,
                memory_context=memory_context,
                additional_context={
                    "delegated_by": "orchestrator",
                    "step": step.get("step"),
                },
            )

            result = await agent.run(
                task=delegated_prompt,
                context=agent_context,
            )

            results.append(result)
            previous_results.append(result.content)

            # Guardar resultado parcial
            await self._store_result(
                project_id=context.project_id,
                session_id=context.session_id,
                result=result,
                delegated_to=agent_role,
                step=step.get("step"),
            )

            # Si falla un paso crítico, detener
            if not result.success and step.get("critical", False):
                logger.error(
                    "critical_step_failed",
                    step=step.get("step"),
                    agent=agent_role,
                )
                break

        # Consolidar resultados
        consolidated = self._consolidate_results(results)

        return AgentResult(
            success=all(r.success for r in results),
            content=consolidated,
            metadata={
                "plan_id": plan.plan_id,
                "steps_executed": len(results),
                "agents_involved": [step.get("agent") for step in plan.steps[: len(results)]],
                "individual_results": [r.to_dict() for r in results],
            },
        )

    async def _create_execution_plan(
        self,
        task: str,
        analysis: TaskAnalysis,
        context: AgentContext,
    ) -> TaskPlan:
        """
        Crea un plan de ejecución detallado.

        Args:
            task: Tarea original
            analysis: Análisis de la tarea
            context: Contexto de ejecución

        Returns:
            TaskPlan con los pasos a ejecutar
        """
        import uuid

        # Extraer plan de los metadatos del análisis
        raw_plan = analysis.metadata.get("raw_response", {}).get("plan", {})

        steps = []
        for i, step_data in enumerate(raw_plan.get("steps", []), 1):
            agent_str = step_data.get("agent", "backend")
            try:
                agent_role = AgentRole(agent_str.lower())
            except ValueError:
                agent_role = AgentRole.BACKEND

            steps.append(
                {
                    "step": i,
                    "agent": agent_role,
                    "task": step_data.get("task", ""),
                    "context": step_data.get("context", ""),
                    "dependencies": step_data.get("dependencies", []),
                    "estimated_time_minutes": step_data.get("estimated_time_minutes", 15),
                    "critical": i <= 2,  # Los primeros pasos son críticos
                }
            )

        # Si no hay pasos del LLM, crear plan inferido
        if not steps:
            steps = self._infer_steps_from_agents(analysis.required_agents, task)

        return TaskPlan(
            plan_id=str(uuid.uuid4()),
            description=raw_plan.get("description", task),
            steps=steps,
            assigned_agents={step["agent"].value: step["agent"] for step in steps},
            estimated_time=sum(s.get("estimated_time_minutes", 15) for s in steps),
        )

    def _infer_steps_from_agents(
        self,
        agents: List[AgentRole],
        task: str,
    ) -> List[Dict[str, Any]]:
        """
        Infiere pasos básicos basado en los agentes necesarios.

        Args:
            agents: Lista de agentes necesarios
            task: Tarea original

        Returns:
            Lista de pasos inferidos
        """
        steps = []
        for i, agent in enumerate(agents, 1):
            steps.append(
                {
                    "step": i,
                    "agent": agent,
                    "task": f"Ejecutar parte de: {task}",
                    "context": "",
                    "dependencies": [agents[i - 2].value] if i > 1 else [],
                    "estimated_time_minutes": 20,
                    "critical": i == 1,
                }
            )
        return steps

    def _consolidate_results(self, results: List[AgentResult]) -> str:
        """
        Consolida los resultados de múltiples agentes.

        Args:
            results: Lista de resultados de agentes

        Returns:
            Texto consolidado
        """
        if not results:
            return "No se obtuvieron resultados."

        parts = ["## Resultado Consolidado\n"]

        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            parts.append(f"\n### Paso {i} [{status}]\n")
            parts.append(result.content[:500])
            if len(result.content) > 500:
                parts.append("...")

        return "\n".join(parts)

    async def _store_result(
        self,
        project_id: str,
        session_id: str,
        result: AgentResult,
        delegated_to: str,
        step: Optional[int] = None,
    ) -> None:
        """
        Almacena un resultado en memoria.

        Args:
            project_id: ID del proyecto
            session_id: ID de la sesión
            result: Resultado a almacenar
            delegated_to: Agente al que se delegó
            step: Número de paso (si aplica)
        """
        try:
            await self._memory_store.store_context(
                project_id=project_id,
                content=f"[Orchestrator → {delegated_to}] {result.content[:500]}",
                memory_type="episodic",
                metadata={
                    "session_id": session_id,
                    "delegated_to": delegated_to,
                    "step": step,
                    "success": result.success,
                },
            )
        except Exception as e:
            logger.warning(
                "result_storage_failed",
                project_id=project_id,
                error=str(e),
            )

    def get_status(self) -> AgentStatus:
        """Retorna el estado actual del agente."""
        return self._status

    def __repr__(self) -> str:
        return f"<OrchestratorAgent(status={self._status.value})>"


# Exportaciones
__all__ = [
    "OrchestratorAgent",
    "TaskType",
    "TaskComplexity",
    "TaskAnalysis",
    "TaskPlan",
]
