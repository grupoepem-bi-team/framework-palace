"""
Agente QA - Palace Framework

Este agente se especializa en calidad de software:
- Tests unitarios e integración
- Análisis de cobertura
- Revisiones de calidad
- Detección de bugs
- Validación de mejores prácticas
- Escaneo de seguridad

Modelo asignado: gemma4:31b
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import uuid4

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentRole, AgentState, Task, TaskStatus
from palace.core.types import AgentCapability, SessionContext
from palace.llm import LLMClient
from palace.memory.base import MemoryType, SearchQuery

if TYPE_CHECKING:
    from palace.memory import MemoryStore

logger = structlog.get_logger()


class QATaskType(str, Enum):
    """Tipos de tareas que puede manejar el agente QA."""

    UNIT_TEST = "unit_test"
    """Crear tests unitarios."""

    INTEGRATION_TEST = "integration_test"
    """Crear tests de integración."""

    E2E_TEST = "e2e_test"
    """Crear tests end-to-end."""

    COVERAGE_ANALYSIS = "coverage_analysis"
    """Analizar cobertura de código."""

    CODE_QUALITY = "code_quality"
    """Revisar calidad del código."""

    SECURITY_SCAN = "security_scan"
    """Escanear vulnerabilidades de seguridad."""

    BUG_DETECTION = "bug_detection"
    """Detectar potenciales bugs."""

    PERFORMANCE_TEST = "performance_test"
    """Crear tests de rendimiento."""

    REVIEW_TESTS = "review_tests"
    """Revisar tests existentes."""


@dataclass
class QACapabilities:
    """Capacidades específicas del agente QA."""

    testing_frameworks: List[str] = field(
        default_factory=lambda: [
            "pytest",
            "unittest",
            "jest",
            "mocha",
            "cypress",
            "playwright",
            "selenium",
            "locust",
        ]
    )

    coverage_tools: List[str] = field(
        default_factory=lambda: [
            "coverage",
            "pytest-cov",
            "istanbul",
            "nyc",
            "jacoco",
        ]
    )

    security_tools: List[str] = field(
        default_factory=lambda: [
            "bandit",
            "safety",
            "dependency-check",
            "snyk",
            "sonarqube",
        ]
    )

    quality_tools: List[str] = field(
        default_factory=lambda: [
            "pylint",
            "flake8",
            "mypy",
            "ruff",
            "black",
            "isort",
            "eslint",
            "prettier",
        ]
    )


@dataclass
class TestResult:
    """Resultado de un test."""

    test_name: str
    """Nombre del test."""

    status: str
    """Estado del test (passed, failed, skipped)."""

    duration_ms: int
    """Duración en milisegundos."""

    message: Optional[str] = None
    """Mensaje de error si falló."""

    coverage_percent: Optional[float] = None
    """Porcentaje de cobertura."""


@dataclass
class QualityReport:
    """Reporte de calidad de código."""

    file_path: str
    """Archivo analizado."""

    score: float
    """Puntuación de calidad (0-100)."""

    issues: List[Dict[str, Any]]
    """Lista de problemas encontrados."""

    suggestions: List[str]
    """Sugerencias de mejora."""

    metrics: Dict[str, Any]
    """Métricas de calidad."""


class QAAgent(AgentBase):
    """
    Agente especializado en calidad de software (QA).

    Este agente maneja todas las tareas relacionadas con:
    - Creación y revisión de tests
    - Análisis de cobertura
    - Escaneo de seguridad
    - Detección de bugs
    - Validación de código

    Modelo: gemma4:31b
    Capacidades: QUALITY_ASSURANCE, TESTING, SECURITY

    Ejemplo:
        agent = QAAgent(llm_client=llm_client)
        result = await agent.run(
            task="Create unit tests for user service",
            context=context,
            memory=memory,
        )
    """

    name: str = "qa"
    role: AgentRole = AgentRole.QA
    model: str = "gemma4:31b"
    description: str = (
        "Agente especializado en calidad de software y testing. "
        "Crea tests unitarios, de integración y E2E, analiza cobertura, "
        "detecta vulnerabilidades de seguridad y valida mejores prácticas de código."
    )

    capabilities: List[AgentCapability] = [
        AgentCapability.QUALITY_ASSURANCE,
        AgentCapability.TESTING,
        AgentCapability.CODE_REVIEW,
    ]

    tools: List[str] = [
        "linter",
        "test_runner",
        "coverage_analyzer",
        "security_scanner",
        "file_reader",
        "file_writer",
    ]

    # Prompts específicos del agente QA
    system_prompt: str = """Eres un experto en calidad de software y testing.

Tu rol es garantizar la calidad del código mediante:
- Creación de tests exhaustivos (unitarios, integración, E2E)
- Análisis de cobertura y detección de gaps
- Detección de vulnerabilidades de seguridad
- Validación de mejores prácticas
- Revisión de código para detectar bugs

Tus responsabilidades específicas:
1. Crear tests que cubran casos edge y escenarios de error
2. Analizar cobertura y sugerir mejoras
3. Detectar vulnerabilidades de seguridad comunes
4. Validar que el código cumple estándares de calidad
5. Revisar tests existentes y sugerir mejoras

Framework de tests que dominas:
- Python: pytest, unittest, pytest-cov
- JavaScript: Jest, Mocha, Cypress
- E2E: Playwright, Selenium

Principios de calidad:
- Un test debe ser independiente, repetible y determinístico
- Los tests deben documentar el comportamiento esperado
- La cobertura mínima aceptable es 80%
- Siempre considerar casos edge y errores
- Los tests de integración validan la interacción entre componentes

Cuando generes tests:
1. Incluir test cases para: happy path, edge cases, error handling
2. Usar fixtures y mocks apropiadamente
3. Nombrar tests descriptivamente (test_<method>_<scenario>)
4. Incluir assertions claras y específicas
5. Agregar docstrings que expliquen el propósito

Formato de respuesta:
- Explica brevemente tu enfoque
- Proporciona el código de test completo
- Indica cómo ejecutar los tests
- Menciona la cobertura esperada
- Sugiere mejoras si aplica"""

    unit_test_prompt: str = """Genera tests unitarios exhaustivos para el siguiente código.

Código a testear:
```{language}
{code}
```

Requisitos:
1. Tests para happy path
2. Tests para edge cases
3. Tests para casos de error
4. Tests para casos límite
5. Usar mocks para dependencias externas
6. Incluir fixtures necesarias
7. Documentar cada test con docstring

Framework: {framework}
Cobertura objetivo: {coverage_target}%

Genera el código de test completo con:
- Imports necesarios
- Fixtures
- Test class o funciones
- Assertions claras
- Setup y teardown si es necesario"""

    integration_test_prompt: str = """Genera tests de integración para el siguiente módulo.

Módulo: {module_name}
Descripción: {description}
Dependencias: {dependencies}

Los tests de integración deben:
1. Probar la interacción entre componentes reales
2. Usar base de datos de prueba si es necesario
3. Validar el flujo completo de datos
4. Probar puntos de integración
5. Incluir cleanup apropiado

Framework: {framework}
Genera tests que validen:
- Conexiones entre servicios
- Flujos de datos end-to-end
- Manejo de errores en la cadena
- Transacciones si aplica"""

    security_scan_prompt: str = """Realiza un análisis de seguridad del siguiente código.

Código:
```{language}
{code}
```

Busca las siguientes vulnerabilidades:
1. Inyección SQL
2. Inyección de comandos
3. XSS (Cross-Site Scripting)
4. CSRF
5. Exposición de datos sensibles
6. Autenticación rota
7. Control de acceso inadecuado
8. Criptografía débil
9. Deserialización insegura
10. Dependencias vulnerables

Para cada vulnerabilidad encontrada:
- Severidad (Critical, High, Medium, Low)
- Descripción del problema
- Línea(s) afectada(s)
- Explotación potencial
- Remedación sugerida
- Código de ejemplo para fix

Genera un reporte de seguridad estructurado."""

    code_quality_prompt: str = """Analiza la calidad del siguiente código.

Código:
```{language}
{code}
```

Evalúa según los siguientes criterios:

1. Legibilidad (0-20 puntos)
   - Nombres descriptivos
   - Estructura clara
   - Comentarios apropiados

2. Mantenibilidad (0-20 puntos)
   - Principio de responsabilidad única
   - DRY (Don't Repeat Yourself)
   - Separación de concerns

3. Performance (0-20 puntos)
   - Eficiencia algorítmica
   - Manejo de recursos
   - Optimización

4. Seguridad (0-20 puntos)
   - Validación de inputs
   - Manejo de errores
   - Protección de datos

5. Testabilidad (0-20 puntos)
   - Facilidad para crear tests
   - Dependencias inyectables
   - Funciones puras

Puntuación total: {total}/100

Para cada criterio:
- Puntuación actual
- Problemas encontrados
- Sugerencias de mejora
- Código refactorizado de ejemplo"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        capabilities: Optional[QACapabilities] = None,
        tools: Optional[List[str]] = None,
    ):
        """
        Inicializa el agente QA.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas de QA (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=cast("LLMClient", llm_client),
            tools=tools or self.tools,
        )
        self._capabilities_config = capabilities or QACapabilities()
        self._test_results: List[TestResult] = []
        self._quality_reports: List[QualityReport] = []

        logger.info(
            "qa_agent_initialized",
            model=self.model,
            capabilities=[c.value for c in self.capabilities],
        )

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente QA.

        Returns:
            Prompt del sistema como cadena
        """
        return self.system_prompt

    def _get_description(self) -> str:
        """
        Obtiene la descripción del agente QA.

        Returns:
            Descripción del agente como cadena
        """
        return self.description

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Evalúa si la tarea está relacionada con:
        - Testing y calidad de software
        - Tests unitarios, integración, E2E
        - Análisis de cobertura
        - Escaneo de seguridad
        - Detección de bugs
        - Revisión de código

        Args:
            task: Tarea a evaluar

        Returns:
            True si el agente puede manejar la tarea
        """
        if not task.description:
            return False

        description_lower = task.description.lower()

        # Keywords de QA
        qa_keywords = [
            "test",
            "testing",
            "unit test",
            "integration test",
            "e2e",
            "coverage",
            "quality",
            "bug",
            "regression",
            "qa",
            "quality assurance",
            "lint",
            "linter",
            "security scan",
            "vulnerability",
            "vulnerabilidad",
            "pytest",
            "jest",
            "mocha",
            "cypress",
            "playwright",
            "selenium",
            "test unitario",
            "test de integración",
            "cobertura",
            "calidad",
            "seguridad",
            "defecto",
            "rendimiento",
            "performance test",
            "load test",
            "stress test",
            "benchmark",
            "locust",
            "bandit",
            "safety",
            "owasp",
            "review test",
            "revisar test",
            "mejorar test",
            "refactor test",
            "test existente",
            "probar",
            "verificar",
            "validar",
            "assert",
            "fixture",
            "mock",
            "stub",
        ]

        # Verificar coincidencias de keywords
        keyword_matches = sum(1 for keyword in qa_keywords if keyword in description_lower)

        if keyword_matches >= 2:
            return True

        # Verificar patrones de test específicos
        test_patterns = [
            r"\btest\b",
            r"\btests\b",
            r"\btesting\b",
            r"\bcoverage\b",
            r"\bpytest\b",
            r"\bjest\b",
            r"\bdescribe\(",
            r"\bit\(",
            r"\bexpect\(",
            r"\bassert",
        ]
        for pattern in test_patterns:
            if re.search(pattern, description_lower):
                return True

        # Si solo hay 1 coincidencia, verificar que sea un indicador fuerte
        if keyword_matches == 1:
            strong_indicators = [
                "test",
                "testing",
                "coverage",
                "bug",
                "qa",
                "quality",
                "pytest",
                "jest",
                "cypress",
                "playwright",
                "security scan",
                "regression",
            ]
            for indicator in strong_indicators:
                if indicator in description_lower:
                    return True

        return False

    async def run(
        self,
        task: Task,
        context: SessionContext,
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de QA.

        Analiza la tarea, determina el tipo de análisis requerido,
        y genera tests, reportes de calidad o escaneos de seguridad.

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión con información del proyecto
            memory: Almacén de memoria para contexto adicional

        Returns:
            Resultado de la ejecución con tests, reportes y sugerencias
        """
        self.state = AgentState.BUSY
        start_time = datetime.utcnow()

        logger.info(
            "qa_agent_executing",
            task_id=task.task_id,
            description=task.description[:100] if task.description else "",
            agent=self.name,
        )

        # Actualizar estado de la tarea
        task.status = TaskStatus.RUNNING

        try:
            # 1. Analizar tipo de tarea
            task_type = self._analyze_task_type(task.description)

            # 2. Recuperar contexto relevante
            retrieved_context = await self._retrieve_context(
                task=task,
                context=context,
                memory=memory,
            )

            # 3. Generar prompt específico según tipo de tarea
            prompt = self._build_prompt(
                task=task,
                task_type=task_type,
                context=retrieved_context,
            )

            # 4. Invocar LLM
            response = await self.invoke_llm(prompt=prompt)

            # 5. Procesar respuesta
            result = self._process_response(
                response=response,
                task_type=task_type,
                task=task,
            )

            # 6. Validar tests si se generaron
            if task_type in [QATaskType.UNIT_TEST, QATaskType.INTEGRATION_TEST]:
                await self._validate_tests(result)

            # 7. Guardar aprendizaje en memoria
            await self._store_learning(
                task=task,
                result=result,
                memory=memory,
            )

            # Actualizar estado
            self.state = AgentState.IDLE

            logger.info(
                "qa_agent_completed",
                task_id=task.task_id,
                task_type=task_type.value,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent=self.name,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(
                "qa_agent_failed",
                task_id=task.task_id,
                error=str(e),
                agent=self.name,
            )

            return AgentResult(
                success=False,
                content="",
                errors=[f"QA task failed: {str(e)}"],
                metadata={"task": task.description, "agent": self.name},
            )

    def _analyze_task_type(self, description: str) -> QATaskType:
        """
        Analiza la descripción de la tarea para determinar su tipo.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de tarea QA
        """
        description_lower = description.lower()

        # Keywords para cada tipo
        keywords = {
            QATaskType.UNIT_TEST: [
                "unit test",
                "test unitario",
                "test individual",
                "pytest",
                "unittest",
                "jest test",
                "probar función",
                "probar método",
            ],
            QATaskType.INTEGRATION_TEST: [
                "integration test",
                "test de integración",
                "test api",
                "test endpoints",
                "test servicios",
                "probar integración",
            ],
            QATaskType.E2E_TEST: [
                "e2e",
                "end-to-end",
                "cypress",
                "playwright",
                "selenium",
                "test flujo completo",
                "test usuario",
            ],
            QATaskType.COVERAGE_ANALYSIS: [
                "coverage",
                "cobertura",
                "cobertura de código",
                "medir cobertura",
                "analizar cobertura",
            ],
            QATaskType.CODE_QUALITY: [
                "calidad",
                "quality",
                "lint",
                "linter",
                "calidad de código",
                "revisión de calidad",
                "clean code",
            ],
            QATaskType.SECURITY_SCAN: [
                "seguridad",
                "security",
                "vulnerabilidad",
                "vulnerability",
                "security scan",
                "escaneo de seguridad",
                "bandit",
                "owasp",
            ],
            QATaskType.BUG_DETECTION: [
                "bug",
                "error",
                "defecto",
                "defect",
                "encontrar error",
                "detectar bug",
                "investigar problema",
            ],
            QATaskType.PERFORMANCE_TEST: [
                "performance",
                "rendimiento",
                "load test",
                "stress test",
                "benchmark",
                "locust",
                "jmeter",
            ],
            QATaskType.REVIEW_TESTS: [
                "review test",
                "revisar test",
                "mejorar test",
                "refactor test",
                "test existente",
            ],
        }

        for task_type, kw_list in keywords.items():
            if any(kw in description_lower for kw in kw_list):
                return task_type

        # Default a unit test si no se puede determinar
        return QATaskType.UNIT_TEST

    async def _retrieve_context(
        self,
        task: Task,
        context: SessionContext,
        memory: Optional["MemoryStore"] = None,
    ) -> Dict[str, Any]:
        """
        Recupera contexto relevante de la memoria y la tarea.

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión
            memory: Almacén de memoria (opcional)

        Returns:
            Contexto recuperado
        """
        retrieved: Dict[str, Any] = {
            "code_files": [],
            "existing_tests": [],
            "quality_standards": [],
            "similar_issues": [],
        }

        # Recuperar código del contexto de la tarea
        if task.context and "code" in task.context:
            retrieved["code_files"].append(
                {
                    "content": task.context["code"],
                    "language": task.context.get("language", "python"),
                    "path": task.context.get("path", "source_code"),
                }
            )

        # Recuperar contexto relevante desde la memoria vectorial
        if memory is not None:
            try:
                search_query = SearchQuery(
                    query=f"tests quality {task.description}",
                    project_id=task.project_id if hasattr(task, "project_id") else None,
                    memory_types=[MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
                    filters={
                        "type": [
                            "test",
                            "test_pattern",
                            "quality_standard",
                            "security_pattern",
                            "error",
                            "solution",
                        ]
                    },
                    top_k=5,
                )
                results = await memory.search(search_query)

                if results:
                    for result in results:
                        entry = result.entry
                        entry_type = entry.metadata.get("type", entry.memory_type.value)
                        content = entry.content

                        if entry_type in ("test", "test_pattern"):
                            retrieved["existing_tests"].append(content)
                        elif entry_type in ("error", "solution"):
                            retrieved["similar_issues"].append(f"- [{entry_type}] {content}")
                        else:
                            retrieved["quality_standards"].append(content)

            except Exception as e:
                logger.warning(
                    "qa_context_retrieval_failed",
                    error=str(e),
                    agent=self.name,
                )

        # Recuperar código del contexto de sesión si existe
        if hasattr(context, "project_context") and context.project_context:
            project = context.project_context
            if hasattr(project, "files"):
                for file_info in project.files[:5]:
                    if isinstance(file_info, dict) and file_info.get("path", "").endswith(
                        (".py", ".js", ".ts", ".java", ".go")
                    ):
                        retrieved["code_files"].append(file_info)

        # Agregar estándares de calidad por defecto
        retrieved["quality_standards"].extend(
            [
                "Cobertura mínima: 80%",
                "Tests deben ser independientes",
                "Usar fixtures para datos de prueba",
                "Incluir tests para edge cases",
                "Documentar propósito de cada test",
            ]
        )

        return retrieved

    def _build_prompt(
        self,
        task: Task,
        task_type: QATaskType,
        context: Dict[str, Any],
    ) -> str:
        """
        Construye el prompt específico según el tipo de tarea.

        Args:
            task: Definición de la tarea
            task_type: Tipo de tarea
            context: Contexto recuperado

        Returns:
            Prompt completo para el LLM
        """
        prompt_parts = []

        # Agregar descripción de la tarea
        prompt_parts.append(f"Tarea: {task.description}\n")

        # Agregar contexto de código si existe
        if context.get("code_files"):
            prompt_parts.append("Archivos de código relacionados:")
            for file_info in context["code_files"][:3]:
                prompt_parts.append(f"\nArchivo: {file_info.get('path', 'unknown')}")
                prompt_parts.append(f"```{file_info.get('language', 'text')}")
                prompt_parts.append(file_info.get("content", "")[:2000])  # Limitar
                prompt_parts.append("```\n")

        # Agregar tests existentes si hay
        if context.get("existing_tests"):
            prompt_parts.append("Tests existentes relevantes:")
            for test_content in context["existing_tests"][:2]:
                prompt_parts.append(f"```\n{test_content[:1000]}\n```\n")

        # Agregar estándares de calidad
        if context.get("quality_standards"):
            prompt_parts.append("Estándares de calidad a seguir:")
            for standard in context["quality_standards"]:
                prompt_parts.append(f"- {standard}")
            prompt_parts.append("")

        # Seleccionar prompt específico según tipo
        if task_type == QATaskType.UNIT_TEST:
            specific_prompt = self.unit_test_prompt.format(
                language="python",  # Detectar del contexto
                code=context.get("code_files", [{}])[0].get("content", ""),
                framework="pytest",
                coverage_target=80,
            )
        elif task_type == QATaskType.INTEGRATION_TEST:
            specific_prompt = self.integration_test_prompt.format(
                module_name=task.description.split()[0] if task.description else "module",
                description=task.description,
                dependencies=",".join(["database", "api", "services"]),
                framework="pytest",
            )
        elif task_type == QATaskType.SECURITY_SCAN:
            specific_prompt = self.security_scan_prompt.format(
                language="python",
                code=context.get("code_files", [{}])[0].get("content", ""),
            )
        elif task_type == QATaskType.CODE_QUALITY:
            specific_prompt = self.code_quality_prompt.format(
                language="python",
                code=context.get("code_files", [{}])[0].get("content", ""),
            )
        else:
            specific_prompt = f"Realiza {task_type.value} para el código proporcionado."

        prompt_parts.append(specific_prompt)

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        task_type: QATaskType,
        task: Task,
    ) -> AgentResult:
        """
        Procesa la respuesta del LLM y extrae información estructurada.

        Args:
            response: Respuesta del LLM
            task_type: Tipo de tarea
            task: Tarea original

        Returns:
            Resultado estructurado del agente
        """
        # Extraer bloques de código
        code_blocks = self._extract_code_blocks(response)

        # Extraer archivos generados
        files_created = []
        for i, block in enumerate(code_blocks):
            filename = self._infer_filename(block, task_type, i)
            files_created.append(
                {
                    "path": filename,
                    "content": block["code"],
                    "language": block["language"],
                }
            )

        # Extraer comandos de ejecución
        commands = self._extract_commands(response)

        # Extraer métricas de cobertura estimada
        coverage = self._extract_coverage(response)

        # Construir metadata del resultado
        metadata = {
            "task_type": task_type.value,
            "files_created": [f["path"] for f in files_created],
            "commands": commands,
            "estimated_coverage": coverage,
            "agent": self.name,
            "model": self.model,
        }

        # Construir lista de artefactos
        artifacts = []
        for i, block in enumerate(code_blocks):
            artifacts.append(
                {
                    "type": "test",
                    "language": block["language"],
                    "content": block["code"],
                    "index": i + 1,
                    "metadata": {
                        "task_id": task.task_id,
                        "task_type": task_type.value,
                    },
                }
            )

        # Crear resultado
        result = AgentResult(
            success=True,
            content=response,
            artifacts=artifacts,
            metadata=metadata,
        )

        return result

    def _extract_code_blocks(self, response: str) -> List[Dict[str, str]]:
        """
        Extrae bloques de código de la respuesta.

        Args:
            response: Respuesta del LLM

        Returns:
            Lista de bloques de código con lenguaje y código
        """
        blocks = []

        # Patrón para bloques de código markdown
        pattern = r"```(\w+)?\n(.*?)```"
        matches = re.findall(pattern, response, re.DOTALL)

        for language, code in matches:
            blocks.append(
                {
                    "language": language or "text",
                    "code": code.strip(),
                }
            )

        return blocks

    def _infer_filename(
        self,
        block: Dict[str, str],
        task_type: QATaskType,
        index: int,
    ) -> str:
        """
        Infiere el nombre del archivo para un bloque de código.

        Args:
            block: Bloque de código
            task_type: Tipo de tarea
            index: Índice del bloque

        Returns:
            Nombre de archivo inferido
        """
        language = block["language"]
        code = block["code"]

        # Buscar declaraciones de clase o función para inferir nombre
        if language == "python":
            # Buscar clase de test
            class_match = re.search(r"class\s+(\w+)", code)
            if class_match:
                class_name = class_match.group(1)
                # Convertir TestX -> test_x.py
                filename = re.sub(r"([A-Z])", r"_\1", class_name).lower()
                if filename.startswith("_"):
                    filename = filename[1:]
                return f"tests/{filename}.py"

            # Buscar función de test
            func_match = re.search(r"def\s+(test_\w+)", code)
            if func_match:
                return f"tests/test_{index}.py"

        elif language in ["javascript", "typescript"]:
            # Buscar describe o test
            if "describe(" in code or "test(" in code:
                return f"tests/test_{index}.{'spec' if 'spec' in code else 'test'}.js"

        # Default
        ext = (
            "py"
            if language == "python"
            else "js"
            if language in ["javascript", "typescript"]
            else "txt"
        )
        return f"tests/test_{index}.{ext}"

    def _extract_commands(self, response: str) -> List[str]:
        """
        Extrae comandos de ejecución de la respuesta.

        Args:
            response: Respuesta del LLM

        Returns:
            Lista de comandos
        """
        commands = []

        # Buscar comandos típicos
        command_patterns = [
            r"pytest\s+[^\n]+",
            r"npm\s+test[^\n]*",
            r"yarn\s+test[^\n]*",
            r"python\s+-m\s+pytest[^\n]*",
            r"coverage\s+run[^\n]*",
            r"coverage\s+report[^\n]*",
        ]

        for pattern in command_patterns:
            matches = re.findall(pattern, response)
            commands.extend(matches)

        return commands

    def _extract_coverage(self, response: str) -> Dict[str, float]:
        """
        Extrae métricas de cobertura de la respuesta.

        Args:
            response: Respuesta del LLM

        Returns:
            Diccionario con métricas de cobertura
        """
        coverage = {
            "estimated": 0.0,
            "statements": 0.0,
            "branches": 0.0,
            "functions": 0.0,
            "lines": 0.0,
        }

        # Buscar porcentajes de cobertura
        coverage_patterns = [
            (r"cobertura[:\s]+(\d+(?:\.\d+)?)%", "estimated"),
            (r"statements[:\s]+(\d+(?:\.\d+)?)%", "statements"),
            (r"branches[:\s]+(\d+(?:\.\d+)?)%", "branches"),
            (r"functions[:\s]+(\d+(?:\.\d+)?)%", "functions"),
            (r"lines[:\s]+(\d+(?:\.\d+)?)%", "lines"),
        ]

        for pattern, key in coverage_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                coverage[key] = float(match.group(1))

        return coverage

    async def _validate_tests(self, result: AgentResult) -> None:
        """
        Valida los tests generados.

        Verifica que los artefactos de test tengan la estructura básica
        esperada: imports, funciones/clases de test, y assertions.

        Args:
            result: Resultado que contiene los tests
        """
        for artifact in result.artifacts:
            if artifact.get("type") != "test":
                continue

            code = artifact.get("content", "")
            language = artifact.get("language", "")

            validation_notes = []

            # Verificar imports (para Python)
            if language == "python" and not re.search(r"^(import |from )", code, re.MULTILINE):
                validation_notes.append("⚠ Posible falta de imports")

            # Verificar funciones/clases de test
            if language == "python":
                if not re.search(r"(def test_|class Test)", code):
                    validation_notes.append("⚠ No se encontraron funciones/clases de test")
            elif language in ("javascript", "typescript"):
                if not re.search(r"(describe\(|it\(|test\()", code):
                    validation_notes.append("⚠ No se encontraron bloques de test")

            # Verificar assertions
            assertion_patterns = [
                r"assert ",
                r"assertEqual",
                r"assertTrue",
                r"assertFalse",
                r"assertRaises",
                r"expect\(",
                r"assert\(",
                r"should\b",
            ]
            if not any(re.search(p, code) for p in assertion_patterns):
                validation_notes.append("⚠ No se encontraron assertions explícitas")

            # Agregar notas al metadata del artefacto
            if validation_notes:
                artifact.setdefault("validation", {}).setdefault("warnings", []).extend(
                    validation_notes
                )
            else:
                artifact.setdefault("validation", {})["status"] = "passed"

    async def _store_learning(
        self,
        task: Task,
        result: AgentResult,
        memory: Optional["MemoryStore"] = None,
    ) -> None:
        """
        Almacena aprendizaje de la tarea en memoria.

        Solo almacena información útil y evita duplicados.

        Args:
            task: Tarea ejecutada
            result: Resultado de la ejecución
            memory: Almacén de memoria (opcional)
        """
        if memory is None or not result.success or not result.content:
            return

        try:
            # Determinar tipo de memoria
            memory_type = self._infer_memory_type(task.description)

            # Crear metadata para la memoria
            store_metadata = {
                "agent": self.name,
                "model": self.model,
                "task_type": self._analyze_task_type(task.description).value,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Almacenar en memoria como conocimiento
            _ = await memory.store_knowledge(
                project_id=task.project_id if hasattr(task, "project_id") else "",
                title=f"QA: {task.description[:80]}",
                content=result.content[:1000],  # Limitar tamaño
                tags=[memory_type, self._analyze_task_type(task.description).value],
                metadata=store_metadata,
            )

            logger.debug(
                "qa_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "qa_learning_store_failed",
                error=str(e),
                agent=self.name,
            )

    def _infer_memory_type(self, description: str) -> str:
        """
        Infiere el tipo de memoria basado en la descripción de la tarea.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de memoria apropiado
        """
        description_lower = description.lower()

        if any(kw in description_lower for kw in ["error", "fallo", "falló", "failed", "bug"]):
            return "errors"
        elif any(
            kw in description_lower
            for kw in ["solución", "solution", "resolver", "fix", "arreglar"]
        ):
            return "solutions"
        elif any(kw in description_lower for kw in ["config", "configuración", "setup", "ajuste"]):
            return "configs"
        elif any(
            kw in description_lower
            for kw in ["patrón", "pattern", "mejor práctica", "best practice", "arquitectura"]
        ):
            return "patterns"
        elif any(
            kw in description_lower
            for kw in ["anti-patrón", "antipattern", "evitar", "no hacer", "mal práctica"]
        ):
            return "anti-patterns"
        else:
            return "patterns"

    # -------------------------------------------------------------------------
    # Métodos de conveniencia para tareas específicas
    # -------------------------------------------------------------------------

    async def create_unit_tests(
        self,
        code: str,
        language: str = "python",
        framework: str = "pytest",
        coverage_target: float = 80.0,
        memory: Optional["MemoryStore"] = None,
    ) -> AgentResult:
        """
        Crea tests unitarios para código dado.

        Args:
            code: Código a testear
            language: Lenguaje de programación
            framework: Framework de testing
            coverage_target: Objetivo de cobertura
            memory: Almacén de memoria (opcional)

        Returns:
            Resultado con tests generados
        """
        task = Task(
            task_id=f"qa-unit-{datetime.utcnow().timestamp()}",
            description=f"Create unit tests for the following {language} code using {framework}",
            project_id="temp",
            context={"code": code, "language": language, "framework": framework},
        )

        context = SessionContext(project_id=uuid4())

        return await self.run(task, context, cast("MemoryStore", memory))

    async def analyze_code_quality(
        self,
        code: str,
        language: str = "python",
        memory: Optional["MemoryStore"] = None,
    ) -> AgentResult:
        """
        Analiza la calidad del código.

        Args:
            code: Código a analizar
            language: Lenguaje de programación
            memory: Almacén de memoria (opcional)

        Returns:
            Resultado con reporte de calidad
        """
        task = Task(
            task_id=f"qa-quality-{datetime.utcnow().timestamp()}",
            description=f"Analyze the quality of the following {language} code",
            project_id="temp",
            context={"code": code, "language": language},
        )

        context = SessionContext(project_id=uuid4())

        return await self.run(task, context, cast("MemoryStore", memory))

    async def scan_security(
        self,
        code: str,
        language: str = "python",
        memory: Optional["MemoryStore"] = None,
    ) -> AgentResult:
        """
        Escanea el código en busca de vulnerabilidades de seguridad.

        Args:
            code: Código a escanear
            language: Lenguaje de programación
            memory: Almacén de memoria (opcional)

        Returns:
            Resultado con reporte de seguridad
        """
        task = Task(
            task_id=f"qa-security-{datetime.utcnow().timestamp()}",
            description=f"Scan the following {language} code for security vulnerabilities",
            project_id="temp",
            context={"code": code, "language": language},
        )

        context = SessionContext(project_id=uuid4())

        return await self.run(task, context, cast("MemoryStore", memory))

    def get_test_results(self) -> List[TestResult]:
        """
        Obtiene los resultados de tests ejecutados.

        Returns:
            Lista de resultados de tests
        """
        return self._test_results

    def get_quality_reports(self) -> List[QualityReport]:
        """
        Obtiene los reportes de calidad generados.

        Returns:
            Lista de reportes de calidad
        """
        return self._quality_reports

    def __repr__(self) -> str:
        return f"<QAAgent(name='{self.name}', model='{self.model}')>"
