"""
Agente Reviewer - Palace Framework

Este agente se especializa en revisión de código, análisis arquitectural
y validación de mejores prácticas. Es el guardián de la calidad del código.

Responsabilidades:
- Revisión de código (code review)
- Análisis de arquitectura
- Detección de problemas de seguridad
- Sugerencias de mejora
- Validación de estándares
- Análisis de performance
- Verificación de patrones de diseño

Modelo asignado: mistral-large
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.agents.base import AgentBase, AgentCapabilities, AgentResult, AgentState, Task
from palace.agents.base import AgentRole as BaseAgentRole
from palace.core.types import AgentCapability, AgentRole, TaskDefinition
from palace.llm.client import LLMClient

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.memory import MemoryStore

logger = structlog.get_logger()


class ReviewType(str, Enum):
    """Tipos de revisión que puede realizar el agente."""

    CODE_REVIEW = "code_review"
    """Revisión general de código."""

    ARCHITECTURE_REVIEW = "architecture_review"
    """Análisis de arquitectura del sistema."""

    SECURITY_REVIEW = "security_review"
    """Análisis de seguridad y vulnerabilidades."""

    PERFORMANCE_REVIEW = "performance_review"
    """Análisis de rendimiento y optimización."""

    STYLE_REVIEW = "style_review"
    """Verificación de estilo y convenciones."""

    PR_REVIEW = "pr_review"
    """Revisión de Pull Request completa."""

    DESIGN_REVIEW = "design_review"
    """Revisión de diseño y patrones."""


class ReviewSeverity(str, Enum):
    """Niveles de severidad para hallazgos de revisión."""

    CRITICAL = "critical"
    """Problema crítico que debe solucionarse inmediatamente."""

    HIGH = "high"
    """Problema importante que debe solucionarse pronto."""

    MEDIUM = "medium"
    """Problema moderado que debería solucionarse."""

    LOW = "low"
    """Problema menor, nice to have."""

    INFO = "info"
    """Sugerencia informativa, no requiere acción."""

    POSITIVE = "positive"
    """Aspecto positivo del código."""


@dataclass
class ReviewFinding:
    """
    Hallazgo de revisión.

    Representa un problema, sugerencia o comentario encontrado
    durante la revisión del código.
    """

    id: str
    """Identificador único del hallazgo."""

    title: str
    """Título corto del hallazgo."""

    description: str
    """Descripción detallada del hallazgo."""

    severity: ReviewSeverity
    """Nivel de severidad."""

    review_type: ReviewType
    """Tipo de revisión."""

    file_path: Optional[str] = None
    """Ruta del archivo afectado."""

    line_start: Optional[int] = None
    """Línea de inicio del problema."""

    line_end: Optional[int] = None
    """Línea de fin del problema."""

    suggestion: Optional[str] = None
    """Sugerencia de solución."""

    code_snippet: Optional[str] = None
    """Fragmento de código relevante."""

    references: List[str] = field(default_factory=list)
    """Referencias a documentación o mejores prácticas."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Metadatos adicionales."""


@dataclass
class ReviewResult:
    """
    Resultado completo de una revisión.

    Contiene todos los hallazgos, resumen y recomendaciones
    generadas durante la revisión.
    """

    review_id: str
    """Identificador único de la revisión."""

    review_type: ReviewType
    """Tipo de revisión realizada."""

    overall_score: float
    """Puntuación general (0-100)."""

    findings: List[ReviewFinding]
    """Lista de hallazgos."""

    summary: str
    """Resumen ejecutivo de la revisión."""

    recommendations: List[str]
    """Recomendaciones principales."""

    approved: bool
    """Si el código está aprobado o no."""

    blocked_reasons: List[str] = field(default_factory=list)
    """Razones por las que el código está bloqueado."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Metadatos adicionales."""

    created_at: datetime = field(default_factory=datetime.utcnow)
    """Timestamp de creación."""

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario."""
        return {
            "review_id": self.review_id,
            "review_type": self.review_type.value,
            "overall_score": self.overall_score,
            "findings_count": len(self.findings),
            "findings_by_severity": {
                severity.value: len([f for f in self.findings if f.severity == severity])
                for severity in ReviewSeverity
            },
            "summary": self.summary,
            "recommendations": self.recommendations,
            "approved": self.approved,
            "blocked_reasons": self.blocked_reasons,
            "created_at": self.created_at.isoformat(),
        }


class ReviewerAgent(AgentBase):
    """
    Agente especializado en revisión de código y arquitectura.

    Este agente es responsable de:
    - Revisar código en busca de problemas y mejoras
    - Analizar la arquitectura del sistema
    - Detectar vulnerabilidades de seguridad
    - Verificar el cumplimiento de estándares
    - Sugerir mejoras de rendimiento
    - Validar patrones de diseño

    Modelo: mistral-large (especializado en análisis y razonamiento)

    Capacidades:
    - CODE_REVIEW: Revisión detallada de código
    - ARCHITECTURE: Análisis arquitectural
    - TESTING: Evaluación de cobertura de pruebas

    Ejemplo de uso:
        agent = ReviewerAgent(llm_client)
        result = await agent.run(
            task="Revisa el código del archivo src/api/users.py",
            context=session_context,
            memory=memory_store
        )
    """

    name: str = "reviewer"
    model: str = "mistral-large"
    role: BaseAgentRole = BaseAgentRole.REVIEWER

    capabilities: AgentCapabilities = AgentCapabilities(
        code_review=True,
        design=True,
        testing=True,
    )

    tools: List[str] = [
        "file_read",
        "file_search",
        "git_diff",
        "git_log",
        "linter",
        "complexity_analyzer",
        "security_scanner",
    ]

    # System prompts específicos por tipo de revisión
    SYSTEM_PROMPTS = {
        ReviewType.CODE_REVIEW: """Eres un revisor de código senior especializado en encontrar problemas y sugerir mejoras.

Tu objetivo es realizar revisiones de código exhaustivas y constructivas.

Analiza el código buscando:
1. **Errores y bugs**: Lógica incorrecta, edge cases no manejados, errores potenciales
2. **Problemas de seguridad**: Vulnerabilidades, datos sensibles expuestos, validaciones faltantes
3. **Rendimiento**: Ineficiencias, consultas N+1, memory leaks, recursos no liberados
4. **Mantenibilidad**: Código difícil de entender, nombres poco claros, funciones muy largas
5. **Testing**: Cobertura insuficiente, tests faltantes, tests frágiles
6. **Buenas prácticas**: Violaciones de principios SOLID, patrones incorrectos, código duplicado
7. **Estilo y convenciones**: Formato inconsistente, convenciones no seguidas

Formato de revisión:
- Proporciona una puntuación general (0-100)
- Lista cada hallazgo con nivel de severidad
- Incluye fragmentos de código relevantes
- Sugiere soluciones específicas con código de ejemplo
- Menciona referencias a documentación o mejores prácticas

Sé constructivo y específico. No digas "esto está mal" sin explicar por qué y cómo mejorarlo.
Proporciona ejemplos de código cuando sea posible.
Celebra el buen código mencionando aspectos positivos.""",
        ReviewType.ARCHITECTURE_REVIEW: """Eres un arquitecto de software senior especializado en diseño de sistemas.

Tu objetivo es evaluar la arquitectura del sistema y proponer mejoras.

Analiza la arquitectura buscando:
1. **Cohesión y acoplamiento**: Componentes bien definidos, dependencias claras
2. **Separación de responsabilidades**: Capas bien diferenciadas, single responsibility
3. **Escalabilidad**: Capacidad de crecer sin cambios arquitectónicos mayores
4. **Mantenibilidad**: Facilidad de modificar y extender el sistema
5. **Patrones de diseño**: Uso apropiado de patrones, anti-patrones
6. **Comunicación entre componentes**: APIs claras, contratos bien definidos
7. **Persistencia y datos**: Modelos de datos, estrategias de cache, consistencia
8. **Seguridad**: Defensa en profundidad, superficie de ataque

Formato de revisión:
- Diagrama de arquitectura actual (descripción textual)
- Análisis de cada componente principal
- Problemas arquitectónicos encontrados
- Deuda técnica identificada
- Propuestas de mejora con prioridad
- Plan de migración si aplica

Usa terminología técnica precisa y proporciona justificaciones para cada recomendación.""",
        ReviewType.SECURITY_REVIEW: """Eres un experto en seguridad de aplicaciones especializado en encontrar vulnerabilidades.

Tu objetivo es realizar un análisis de seguridad exhaustivo del código.

Busca vulnerabilidades comunes:
1. **Inyección**: SQL, NoSQL, Command, XSS, Template Injection
2. **Autenticación y autorización**: Controles de acceso, sesiones, passwords
3. **Datos sensibles**: Exposición de datos, logs, errores
4. **Validación de entrada**: Sanitización, encoding, whitelist/blacklist
5. **Criptografía**: Algoritmos débiles, claves hardcodeadas, IVs estáticos
6. **Configuración**: Permisos, features debug, headers de seguridad
7. **Dependencias**: Vulnerabilidades conocidas, versiones obsoletas
8. **OWASP Top 10**: Cross-site scripting, CSRF, SSRF, XXE, etc.

Para cada vulnerabilidad:
- Clasifica la severidad (Critical, High, Medium, Low)
- Describe el impacto potencial
- Proporciona código vulnerable
- Muestra código corregido
- Referencia CVEs, CWEs, o OWASP cuando aplique

Prioriza los problemas críticos y altos. Sé específico sobre el riesgo.""",
        ReviewType.PERFORMANCE_REVIEW: """Eres un ingeniero de rendimiento especializado en optimización de código.

Tu objetivo es identificar cuellos de botella y proponer optimizaciones.

Analiza el rendimiento buscando:
1. **Complejidad algorítmica**: O(n²), O(n³), algoritmos ineficientes
2. **Consultas a base de datos**: N+1, queries sin índices, JOINs costosos
3. **Uso de memoria**: Memory leaks, estructuras ineficientes, caching faltante
4. **I/O**: Lecturas/escrituras innecesarias, operaciones bloqueantes
5. **Red**: Requests innecesarios, payloads grandes, falta de batching
6. **CPU**: Loops costosos, cálculos repetidos, falta de memoización
7. **Concurrencia**: Race conditions, deadlocks, locks innecesarios

Para cada problema:
- Mide el impacto estimado (alto, medio, bajo)
- Identifica el cuello de botella específico
- Proporciona código optimizado
- Estima la mejora esperada
- Considera trade-offs (memoria vs CPU, complejidad vs rendimiento)

Documenta las optimizaciones con benchmarks cuando sea posible.""",
        ReviewType.PR_REVIEW: """Eres un revisor de Pull Requests senior que proporciona feedback completo y constructivo.

Tu objetivo es realizar una revisión completa de PRs.

Verifica:
1. **Descripción del PR**: ¿Explica claramente los cambios?
2. **Tests**: ¿Hay tests nuevos? ¿Pasaron los existentes?
3. **Documentación**: ¿Se actualizó la documentación?
4. **Breaking changes**: ¿Hay cambios que rompen compatibilidad?
5. **Tamaño del PR**: ¿Es manejable o debería dividirse?
6. **Commits**: ¿Son atómicos y con mensajes claros?
7. **Código**: Calidad, estilo, patrones (según code review)
8. **Impacto**: ¿Qué componentes se ven afectados?

Formato de revisión:
- Resumen de cambios
- Lista de archivos modificados con impacto
- Problemas blocking (deben solucionarse)
- Sugerencias (nice to have)
- Preguntas para el autor
- Veredicto: Approve, Request Changes, Comment

Sé específico en tus comentarios. Usa el formato de GitHub para comentarios en línea.""",
        ReviewType.DESIGN_REVIEW: """Eres un experto en diseño de software especializado en patrones y principios.

Tu objetivo es evaluar el diseño del código y proponer mejoras.

Analiza el diseño buscando:
1. **Patrones de diseño**: Uso correcto, anti-patrones, patrones faltantes
2. **Principios SOLID**: SRP, OCP, LSP, ISP, DIP
3. **DRY y KISS**: Código duplicado, complejidad innecesaria
4. **YAGNI**: Funcionalidad no necesaria, over-engineering
5. **Cohesión**: Clases con una responsabilidad, métodos cohesivos
6. **Acoplamiento**: Dependencias innecesarias, interfaces estables
7. **Abstracción**: Niveles correctos, leaky abstractions

Para cada problema de diseño:
- Explica el principio violado
- Muestra el diseño actual
- Propone un diseño mejorado
- Justifica los beneficios
- Considera el contexto del proyecto

Usa diagramas textuales (ASCII o PlantUML) cuando sea útil.""",
        ReviewType.STYLE_REVIEW: """Eres un experto en estilo de código y convenciones.

Tu objetivo es asegurar consistencia y legibilidad del código.

Verifica:
1. **Nomenclatura**: Nombres descriptivos, convenciones del lenguaje
2. **Formato**: Indentación, espaciado, longitud de línea
3. **Organización**: Orden de imports, estructura de clases
4. **Documentación**: Docstrings, comentarios necesarios
5. **Complejidad**: Funciones muy largas, archivos muy grandes
6. **Consistencia**: Estilo uniforme en todo el proyecto

Para cada problema de estilo:
- Indica la convención violada
- Muestra el código actual
- Muestra el código corregido
- Referencia la guía de estilo aplicable

Prioriza problemas que afectan legibilidad y mantenibilidad sobre preferencias personales.""",
    }

    def __init__(self, llm_client: LLMClient):
        """
        Inicializa el agente Reviewer.

        Args:
            llm_client: Cliente LLM para invocar modelos
        """
        super().__init__(
            name=self.name,
            role=BaseAgentRole.REVIEWER,
            model=self.model,
            llm_client=llm_client,
            capabilities=self.capabilities,
            tools=self.tools,
        )
        self._current_task: Optional[str] = None
        self._last_review: Optional[ReviewResult] = None

        logger.info(
            "reviewer_agent_initialized",
            model=self.model,
            capabilities=self.capabilities.to_list(),
        )

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt de sistema por defecto para el agente Reviewer.

        Returns:
            Prompt de sistema para revisiones de código
        """
        return self.SYSTEM_PROMPTS[ReviewType.CODE_REVIEW]

    def _get_description(self) -> str:
        """
        Obtiene una descripción de este agente.

        Returns:
            Cadena de descripción del agente
        """
        return (
            "Agente especializado en revisión de código y arquitectura. "
            "Realiza revisiones de código, análisis de seguridad, "
            "evaluación de rendimiento y validación de estándares. "
            "Modelo: mistral-large."
        )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea dada.

        Verifica si la descripción de la tarea contiene keywords relacionadas
        con revisión, o si las capacidades requeridas coinciden con las del agente.

        Args:
            task: La tarea a evaluar

        Returns:
            True si este agente puede manejar la tarea
        """
        description = task.description.lower()

        # Keywords de revisión en inglés y español
        review_keywords = [
            "review",
            "code review",
            "refactor",
            "audit",
            "quality",
            "best practices",
            "security review",
            "performance review",
            "pr review",
            "pull request",
            "revisar",
            "revisión",
            "auditoría",
            "calidad",
            "mejores prácticas",
            "revisión de seguridad",
            "revisión de rendimiento",
            "arquitectura",
            "architecture",
            "lint",
            "estilo",
            "style",
            "convenciones",
        ]

        if any(keyword in description for keyword in review_keywords):
            return True

        # Verificar capacidades requeridas (si existen en la tarea)
        required_caps = getattr(task, "required_capabilities", None)
        if required_caps:
            reviewer_caps = {
                AgentCapability.CODE_REVIEW,
                AgentCapability.ARCHITECTURE,
                AgentCapability.TESTING,
            }
            if set(required_caps) & reviewer_caps:
                return True

        # Verificar si el agente sugerido es reviewer
        suggested_agent = getattr(task, "suggested_agent", None)
        if suggested_agent and hasattr(suggested_agent, "value"):
            if suggested_agent.value == AgentRole.REVIEWER.value:
                return True

        # Verificar en el contexto de la tarea
        task_context = getattr(task, "context", None) or {}
        if isinstance(task_context, dict):
            context_keywords = str(task_context).lower()
            if any(kw in context_keywords for kw in ["review", "audit", "refactor"]):
                return True

        return False

    async def run(
        self,
        task: TaskDefinition,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de revisión.

        Este es el método principal que coordina todo el proceso de revisión.

        Args:
            task: Definición de la tarea
            context: Contexto de sesión con información del proyecto
            memory: Almacén de memoria para recuperar contexto

        Returns:
            Resultado de la revisión con hallazgos y recomendaciones
        """
        self.state = AgentState.BUSY
        self._current_task = str(task.task_id)

        logger.info(
            "reviewer_agent_started",
            task_id=str(task.task_id),
            description=task.description[:100],
        )

        try:
            # 1. Determinar tipo de revisión
            review_type = self._determine_review_type(task.description)

            # 2. Recuperar contexto relevante
            retrieved_context = await self._retrieve_context(
                task=task.description,
                project_id=str(task.project_id),
                memory=memory,
            )

            # 3. Construir prompt de revisión
            review_prompt = self._build_review_prompt(
                task=task,
                review_type=review_type,
                context=retrieved_context,
            )

            # 4. Ejecutar revisión con LLM
            llm_result = await self.llm_client.invoke(
                prompt=review_prompt,
                role="reviewer",
                system_prompt=self.SYSTEM_PROMPTS.get(
                    review_type, self.SYSTEM_PROMPTS[ReviewType.CODE_REVIEW]
                ),
                temperature=0.3,  # Temperatura baja para análisis más preciso
                max_tokens=8192,
            )

            # 5. Parsear resultado
            review_result = self._parse_review_result(
                llm_response=llm_result.content,
                review_type=review_type,
            )

            # 6. Almacenar resultado en memoria
            await self._store_review_result(
                result=review_result,
                project_id=str(task.project_id),
                memory=memory,
            )

            # 7. Construir resultado final
            agent_result = self._build_agent_result(
                task=task,
                review_result=review_result,
                llm_result=llm_result,
            )

            self._last_review = review_result
            self.state = AgentState.IDLE

            logger.info(
                "reviewer_agent_completed",
                task_id=str(task.task_id),
                review_type=review_type.value,
                findings_count=len(review_result.findings),
                overall_score=review_result.overall_score,
                approved=review_result.approved,
            )

            return agent_result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(
                "reviewer_agent_error",
                task_id=str(task.task_id),
                error=str(e),
            )
            raise

    def _determine_review_type(self, description: str) -> ReviewType:
        """
        Determina el tipo de revisión basado en la descripción.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de revisión determinado
        """
        description_lower = description.lower()

        # Keywords para cada tipo de revisión
        type_keywords = {
            ReviewType.ARCHITECTURE_REVIEW: [
                "arquitectura",
                "architecture",
                "diseño del sistema",
                "estructura",
                "componentes",
                "patrones arquitectónicos",
                "microservicios",
                "monolito",
                "escalabilidad",
            ],
            ReviewType.SECURITY_REVIEW: [
                "seguridad",
                "security",
                "vulnerabilidad",
                "vulnerability",
                "autenticación",
                "authentication",
                "autorización",
                "authorization",
                "ataque",
                "attack",
                "exploit",
                "injection",
            ],
            ReviewType.PERFORMANCE_REVIEW: [
                "rendimiento",
                "performance",
                "optimizar",
                "optimize",
                "lento",
                "slow",
                "cuello de botella",
                "bottleneck",
                "memoria",
                "memory",
                "cpu",
                "latencia",
            ],
            ReviewType.PR_REVIEW: [
                "pull request",
                "pr",
                "merge request",
                "mr",
                "revisar cambios",
                "review changes",
                "código nuevo",
            ],
            ReviewType.DESIGN_REVIEW: [
                "diseño",
                "design",
                "patrón",
                "pattern",
                "solid",
                "dry",
                "kiss",
                "yagni",
                "refactorizar",
                "refactor",
                "reestructurar",
            ],
            ReviewType.STYLE_REVIEW: [
                "estilo",
                "style",
                "convenciones",
                "conventions",
                "formato",
                "format",
                "lint",
                "nomenclatura",
            ],
        }

        # Verificar cada tipo
        for review_type, keywords in type_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return review_type

        # Por defecto, code review
        return ReviewType.CODE_REVIEW

    async def _retrieve_context(
        self,
        task: str,
        project_id: str,
        memory: "MemoryStore",
    ) -> Dict[str, Any]:
        """
        Recupera contexto relevante de la memoria.

        Args:
            task: Descripción de la tarea
            project_id: ID del proyecto
            memory: Almacén de memoria

        Returns:
            Contexto recuperado
        """
        context = {
            "adrs": [],
            "patterns": [],
            "related_files": [],
            "previous_reviews": [],
            "standards": [],
        }

        try:
            # Recuperar ADRs del proyecto
            adrs = await memory.retrieve_context(
                project_id=project_id,
                query=f"architecture decisions {task}",
                top_k=5,
            )
            context["adrs"] = adrs

            # Recuperar patrones de código
            patterns = await memory.retrieve_context(
                project_id=project_id,
                query=f"code patterns style conventions",
                top_k=5,
            )
            context["patterns"] = patterns

            # Recuperar revisiones anteriores
            reviews = await memory.retrieve_context(
                project_id=project_id,
                query=f"code review previous findings",
                top_k=3,
            )
            context["previous_reviews"] = reviews

            logger.debug(
                "context_retrieved",
                project_id=project_id,
                adrs_count=len(context["adrs"]),
                patterns_count=len(context["patterns"]),
            )

        except Exception as e:
            logger.warning(
                "context_retrieval_failed",
                error=str(e),
            )

        return context

    def _build_review_prompt(
        self,
        task: TaskDefinition,
        review_type: ReviewType,
        context: Dict[str, Any],
    ) -> str:
        """
        Construye el prompt de revisión.

        Args:
            task: Definición de la tarea
            review_type: Tipo de revisión
            context: Contexto recuperado

        Returns:
            Prompt completo para la revisión
        """
        prompt_parts = []

        # Encabezado
        prompt_parts.append(f"# Solicitud de Revisión\n")
        prompt_parts.append(f"**Tipo de revisión:** {review_type.value}\n")
        prompt_parts.append(f"**Descripción:** {task.description}\n\n")

        # Contexto del proyecto
        if context.get("adrs"):
            prompt_parts.append("## Decisiones Arquitectónicas Previas\n")
            for adr in context["adrs"][:3]:
                prompt_parts.append(f"- {adr.get('content', '')[:200]}...\n")
            prompt_parts.append("\n")

        if context.get("patterns"):
            prompt_parts.append("## Patrones y Estándares del Proyecto\n")
            for pattern in context["patterns"][:3]:
                prompt_parts.append(f"- {pattern.get('content', '')[:200]}...\n")
            prompt_parts.append("\n")

        if context.get("previous_reviews"):
            prompt_parts.append("## Revisiones Anteriores Relevantes\n")
            for review in context["previous_reviews"][:2]:
                prompt_parts.append(f"- {review.get('content', '')[:200]}...\n")
            prompt_parts.append("\n")

        # Instrucciones específicas según tipo
        prompt_parts.append("## Instrucciones Específicas\n")

        if review_type == ReviewType.CODE_REVIEW:
            prompt_parts.append("""
1. Analiza el código proporcionado buscando:
   - Errores de lógica y bugs potenciales
   - Vulnerabilidades de seguridad
   - Problemas de rendimiento
   - Violaciones de mejores prácticas
   - Código difícil de mantener

2. Para cada hallazgo, proporciona:
   - Severidad: Critical/High/Medium/Low/Info/Positive
   - Archivo y líneas afectadas
   - Descripción clara del problema
   - Código de ejemplo mostrando el problema
   - Sugerencia de corrección con código
   - Referencias a documentación

3. Al final, proporciona:
   - Puntuación general (0-100)
   - Resumen ejecutivo
   - Lista de recomendaciones priorizadas
   - Veredicto: Approved / Needs Changes / Blocked
""")

        elif review_type == ReviewType.ARCHITECTURE_REVIEW:
            prompt_parts.append("""
1. Analiza la arquitectura del sistema:
   - Cohesión y acoplamiento
   - Separación de responsabilidades
   - Patrones de diseño utilizados
   - Escalabilidad y mantenibilidad

2. Proporciona:
   - Descripción de la arquitectura actual
   - Problemas identificados por severidad
   - Deuda técnica detectada
   - Propuestas de mejora priorizadas
   - Diagrama simplificado (descripción textual)

3. Evalúa:
   - Puntuación de arquitectura (0-100)
   - Riesgos principales
   - Recomendaciones de corto y largo plazo
""")

        elif review_type == ReviewType.SECURITY_REVIEW:
            prompt_parts.append("""
1. Realiza un análisis de seguridad:
   - Vulnerabilidades OWASP Top 10
   - Problemas de autenticación/autorización
   - Exposición de datos sensibles
   - Configuraciones inseguras
   - Dependencias vulnerables

2. Para cada vulnerabilidad:
   - Clasifica severidad (Critical/High/Medium/Low)
   - Describe el impacto potencial
   - Muestra código vulnerable
   - Proporciona código corregido
   - Referencia CVE/CWE/OWASP

3. Al final:
   - Puntuación de seguridad (0-100)
   - Lista de problemas blocking
   - Lista de problemas no blocking
   - Recomendaciones priorizadas
""")

        elif review_type == ReviewType.PERFORMANCE_REVIEW:
            prompt_parts.append("""
1. Analiza el rendimiento:
   - Complejidad algorítmica
   - Consultas a base de datos
   - Uso de memoria
   - Operaciones de I/O
   - Posibles cuellos de botella

2. Para cada problema:
   - Severidad del impacto
   - Ubicación en el código
   - Descripción del problema
   - Impacto en rendimiento
   - Solución propuesta
   - Mejora estimada

3. Proporciona:
   - Puntuación de rendimiento (0-100)
   - Problemas críticos de rendimiento
   - Optimizaciones recomendadas
   - Trade-offs a considerar
""")

        elif review_type == ReviewType.PR_REVIEW:
            prompt_parts.append("""
1. Revisa el Pull Request:
   - Descripción y propósito
   - Tests añadidos/modificados
   - Documentación actualizada
   - Breaking changes
   - Impacto en otros componentes

2. Para cada archivo modificado:
   - Cambios significativos
   - Problemas encontrados
   - Sugerencias de mejora

3. Proporciona:
   - Veredicto: APPROVE / REQUEST_CHANGES / COMMENT
   - Issues blocking (deben solucionarse)
   - Sugerencias (nice to have)
   - Preguntas para el autor
""")

        # Formato de respuesta
        prompt_parts.append("\n## Formato de Respuesta\n")
        prompt_parts.append("""
Proporciona tu revisión en el siguiente formato:

### Puntuación General: [0-100]

### Resumen Ejecutivo
[Breve resumen de la revisión]

### Hallazgos

#### [SEVERITY] [Título del Hallazgo]
- **Archivo:** ruta/del/archivo.py
- **Líneas:** X-Y
- **Descripción:** [Descripción detallada]
- **Código problemático:**
```python
[Código con problema]
```
- **Solución propuesta:**
```python
[Código corregido]
```
- **Referencias:** [Links a documentación]

[Repetir para cada hallazgo]

### Recomendaciones
1. [Recomendación 1]
2. [Recomendación 2]
...

### Veredicto
- **Estado:** [APPROVED / NEEDS_CHANGES / BLOCKED]
- **Razones (si blocked):** [Razones]
""")

        return "".join(prompt_parts)

    def _parse_review_result(
        self,
        llm_response: str,
        review_type: ReviewType,
    ) -> ReviewResult:
        """
        Parsea la respuesta del LLM a un ReviewResult.

        Args:
            llm_response: Respuesta del modelo
            review_type: Tipo de revisión

        Returns:
            Resultado de revisión estructurado
        """
        import re
        from uuid import uuid4

        review_id = str(uuid4())
        findings: List[ReviewFinding] = []

        # Extraer puntuación general
        score_match = re.search(r"Puntuación General:\s*(\d+)", llm_response)
        overall_score = float(score_match.group(1)) if score_match else 70.0

        # Extraer hallazgos (simplificado - en producción usar parser más robusto)
        # Buscar patrones como: #### [CRITICAL] Título
        finding_pattern = re.compile(r"####\s*\[(\w+)\]\s*(.+?)(?=####|\n###|$)", re.DOTALL)

        for match in finding_pattern.finditer(llm_response):
            severity_str = match.group(1).upper()
            content = match.group(2)

            # Mapear severidad
            severity_map = {
                "CRITICAL": ReviewSeverity.CRITICAL,
                "HIGH": ReviewSeverity.HIGH,
                "MEDIUM": ReviewSeverity.MEDIUM,
                "LOW": ReviewSeverity.LOW,
                "INFO": ReviewSeverity.INFO,
                "POSITIVE": ReviewSeverity.POSITIVE,
            }
            severity = severity_map.get(severity_str, ReviewSeverity.INFO)

            # Extraer título (primera línea)
            lines = content.strip().split("\n")
            title = lines[0].strip() if lines else "Hallazgo"

            # Extraer archivo si existe
            file_match = re.search(r"\*\*Archivo:\*\*\s*(.+)", content)
            file_path = file_match.group(1).strip() if file_match else None

            # Extraer líneas si existen
            lines_match = re.search(r"\*\*Líneas:\*\*\s*(\d+)(?:-(\d+))?", content)
            line_start = int(lines_match.group(1)) if lines_match else None
            line_end = (
                int(lines_match.group(2)) if lines_match and lines_match.group(2) else line_start
            )

            # Extraer código problemático
            code_match = re.search(r"```[a-z]*\n(.+?)\n```", content, re.DOTALL)
            code_snippet = code_match.group(1).strip() if code_match else None

            finding = ReviewFinding(
                id=str(uuid4()),
                title=title[:100],  # Limitar longitud
                description=content[:500],
                severity=severity,
                review_type=review_type,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                code_snippet=code_snippet[:1000] if code_snippet else None,
            )
            findings.append(finding)

        # Si no se encontraron hallazgos, crear uno genérico
        if not findings:
            findings.append(
                ReviewFinding(
                    id=str(uuid4()),
                    title="Revisión completada",
                    description="La revisión fue completada sin hallazgos específicos.",
                    severity=ReviewSeverity.INFO,
                    review_type=review_type,
                )
            )

        # Extraer resumen
        summary_match = re.search(
            r"### Resumen Ejecutivo\n(.+?)(?=\n###|\Z)", llm_response, re.DOTALL
        )
        summary = summary_match.group(1).strip() if summary_match else "Revisión completada."

        # Extraer recomendaciones
        recommendations = []
        rec_section = re.search(r"### Recomendaciones\n(.+?)(?=\n###|\Z)", llm_response, re.DOTALL)
        if rec_section:
            rec_lines = rec_section.group(1).strip().split("\n")
            recommendations = [
                line.strip().lstrip("0123456789. ").strip()
                for line in rec_lines
                if line.strip() and not line.strip().startswith("#")
            ]

        # Extraer veredicto
        verdict_match = re.search(r"\*\*Estado:\*\*\s*(\w+)", llm_response)
        verdict = verdict_match.group(1).upper() if verdict_match else "NEEDS_CHANGES"

        approved = verdict == "APPROVED"

        # Extraer razones si está bloqueado
        blocked_reasons = []
        if verdict == "BLOCKED":
            reasons_match = re.search(
                r"\*\*Razones.*?:\*\*\s*(.+?)(?=\n###|\Z)", llm_response, re.DOTALL
            )
            if reasons_match:
                blocked_reasons = [
                    r.strip() for r in reasons_match.group(1).strip().split("\n") if r.strip()
                ]

        return ReviewResult(
            review_id=review_id,
            review_type=review_type,
            overall_score=overall_score,
            findings=findings,
            summary=summary,
            recommendations=recommendations,
            approved=approved,
            blocked_reasons=blocked_reasons,
        )

    async def _store_review_result(
        self,
        result: ReviewResult,
        project_id: str,
        memory: "MemoryStore",
    ) -> None:
        """
        Almacena el resultado de la revisión en memoria.

        Args:
            result: Resultado de la revisión
            project_id: ID del proyecto
            memory: Almacén de memoria
        """
        try:
            # Crear contenido para almacenar
            content = f"""
# Revisión de Código - {result.review_type.value}

## Puntuación: {result.overall_score}/100

## Resumen
{result.summary}

## Hallazgos ({len(result.findings)})
"""

            for finding in result.findings:
                content += f"""
### [{finding.severity.value}] {finding.title}
{finding.description}
"""
                if finding.file_path:
                    content += f"**Archivo:** {finding.file_path}\n"
                if finding.line_start:
                    content += f"**Líneas:** {finding.line_start}"
                    if finding.line_end and finding.line_end != finding.line_start:
                        content += f"-{finding.line_end}"
                    content += "\n"

            content += f"""
## Recomendaciones
"""
            for i, rec in enumerate(result.recommendations, 1):
                content += f"{i}. {rec}\n"

            content += f"""
## Veredicto: {"APROBADO" if result.approved else "REQUIERE CAMBIOS"}
"""

            # Almacenar en memoria semántica
            from palace.memory.base import MemoryEntry, MemoryType

            await memory.store(
                MemoryEntry(
                    memory_type=MemoryType.SEMANTIC,
                    project_id=project_id,
                    content=content,
                    source="reviewer",
                    metadata={
                        "review_id": result.review_id,
                        "review_type": result.review_type.value,
                        "score": result.overall_score,
                        "approved": result.approved,
                    },
                )
            )

            logger.debug(
                "review_result_stored",
                review_id=result.review_id,
                project_id=project_id,
            )

        except Exception as e:
            logger.warning(
                "failed_to_store_review_result",
                error=str(e),
            )

    def _build_agent_result(
        self,
        task: TaskDefinition,
        review_result: ReviewResult,
        llm_result: Any,
    ) -> AgentResult:
        """
        Construye el resultado del agente.

        Args:
            task: Definición de la tarea
            review_result: Resultado de la revisión
            llm_result: Resultado del LLM

        Returns:
            Resultado del agente estructurado
        """
        # Convertir hallazgos a formato simplificado
        findings_summary = [
            {
                "severity": f.severity.value,
                "title": f.title,
                "file": f.file_path,
                "lines": f"{f.line_start}-{f.line_end}" if f.line_start else None,
            }
            for f in review_result.findings
        ]

        # Contar por severidad
        severity_counts = {}
        for finding in review_result.findings:
            sev = finding.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        # Construir acciones siguientes como lista de strings
        next_actions = [
            f"fix_critical: {f.title}"
            for f in review_result.findings
            if f.severity == ReviewSeverity.CRITICAL
        ]

        # Construir sugerencias a partir de recomendaciones
        suggestions = review_result.recommendations[:10]  # Limitar a 10

        return AgentResult(
            success=review_result.approved,
            content=review_result.summary,
            artifacts=[
                {
                    "type": "review_findings",
                    "review_id": review_result.review_id,
                    "review_type": review_result.review_type.value,
                    "findings": findings_summary,
                }
            ],
            metadata={
                "review_id": review_result.review_id,
                "review_type": review_result.review_type.value,
                "overall_score": review_result.overall_score,
                "approved": review_result.approved,
                "findings_count": len(review_result.findings),
                "severity_counts": severity_counts,
                "recommendations": review_result.recommendations,
                "blocked_reasons": review_result.blocked_reasons,
                "delegate_to": None,
                "context_updates": {
                    "review_completed": True,
                    "review_score": review_result.overall_score,
                },
                "memory_entries": [
                    {
                        "type": "review",
                        "review_type": review_result.review_type.value,
                        "score": review_result.overall_score,
                    }
                ],
            },
            suggestions=suggestions,
            next_actions=next_actions,
            agent_name=self.name,
            model_used=self.model,
            tokens_used=getattr(llm_result, "total_tokens", 0),
            execution_time_ms=0,  # TODO: calcular
        )

    def get_status(self) -> AgentState:
        """Retorna el estado actual del agente."""
        return self.state

    def get_last_review(self) -> Optional[ReviewResult]:
        """Retorna el último resultado de revisión."""
        return self._last_review

    async def review_code(
        self,
        code: str,
        file_path: Optional[str] = None,
        project_id: Optional[str] = None,
        memory: Optional["MemoryStore"] = None,
    ) -> ReviewResult:
        """
        Método de conveniencia para revisar código directamente.

        Args:
            code: Código a revisar
            file_path: Ruta del archivo (opcional)
            project_id: ID del proyecto (opcional)
            memory: Almacén de memoria (opcional)

        Returns:
            Resultado de la revisión
        """
        description = f"Revisar código"
        if file_path:
            description += f" del archivo {file_path}"

        task = TaskDefinition(
            title="Code Review",
            description=description,
            required_capabilities=[AgentCapability.CODE_REVIEW],
            input_context={"code": code, "file_path": file_path},
        )

        if project_id:
            task.project_id = project_id

        # Crear contexto dummy si no se proporciona
        if memory is None:
            from palace.memory.base import MemoryEntry, MemoryStore, MemoryType

            memory = MemoryStore()

        # Ejecutar revisión
        result = await self.run(
            task=task,
            context=None,  # TODO: crear contexto dummy
            memory=memory,
        )

        return self._last_review

    async def review_pr(
        self,
        diff: str,
        files_changed: List[str],
        project_id: Optional[str] = None,
        memory: Optional["MemoryStore"] = None,
    ) -> ReviewResult:
        """
        Método de conveniencia para revisar un Pull Request.

        Args:
            diff: Diff del PR
            files_changed: Lista de archivos modificados
            project_id: ID del proyecto (opcional)
            memory: Almacén de memoria (opcional)

        Returns:
            Resultado de la revisión
        """
        description = f"Revisar Pull Request con cambios en {len(files_changed)} archivos"

        task = TaskDefinition(
            title="PR Review",
            description=description,
            required_capabilities=[AgentCapability.CODE_REVIEW],
            input_context={
                "diff": diff,
                "files_changed": files_changed,
            },
        )

        if project_id:
            task.project_id = project_id

        if memory is None:
            from palace.memory.base import MemoryStore

            memory = MemoryStore()

        result = await self.run(
            task=task,
            context=None,
            memory=memory,
        )

        return self._last_review


# Exportar clases principales
__all__ = [
    "ReviewerAgent",
    "ReviewType",
    "ReviewSeverity",
    "ReviewFinding",
    "ReviewResult",
]
