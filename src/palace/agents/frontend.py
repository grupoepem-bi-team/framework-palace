"""
Agente Frontend - Palace Framework

Este agente se especializa en desarrollo frontend, incluyendo:
- Componentes UI (React, Vue, Angular, Svelte)
- Estilos y diseño (Tailwind, CSS, SASS)
- Lógica del lado del cliente
- Integración con APIs
- Testing de frontend
- Accesibilidad (a11y)
- Optimización de rendimiento

Modelo: qwen3-coder-next
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentRole, AgentState, Task
from palace.core.types import AgentCapability
from palace.memory.base import MemoryType, SearchQuery

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class FrontendCapabilities:
    """Capacidades específicas del agente Frontend."""

    frameworks: list[str] = field(
        default_factory=lambda: [
            "react",
            "vue",
            "angular",
            "svelte",
            "nextjs",
            "nuxt",
            "sveltekit",
        ]
    )

    styling: list[str] = field(
        default_factory=lambda: [
            "tailwind",
            "css-modules",
            "styled-components",
            "sass",
            "scss",
            "emotion",
            "chakra",
            "material-ui",
        ]
    )

    state_management: list[str] = field(
        default_factory=lambda: [
            "redux",
            "zustand",
            "pinia",
            "context-api",
            "mobx",
            "vuex",
            "ngxs",
        ]
    )

    testing: list[str] = field(
        default_factory=lambda: [
            "jest",
            "vitest",
            "react-testing-library",
            "cypress",
            "playwright",
            "testing-library",
        ]
    )


# =============================================================================
# Palabras clave para detección de tareas
# =============================================================================

FRONTEND_KEYWORDS = [
    # Frameworks y librerías frontend
    "react",
    "vue",
    "angular",
    "svelte",
    "nextjs",
    "next.js",
    "nuxt",
    "nuxtjs",
    "nuxt.js",
    "sveltekit",
    # Componentes y UI
    "component",
    "componente",
    "page",
    "página",
    "layout",
    "template",
    "plantilla",
    "prop",
    "props",
    "state",
    "estado",
    "hook",
    "hooks",
    "usestate",
    "useeffect",
    "usecallback",
    "usememo",
    "useref",
    "context",
    "provider",
    # Estilos y diseño
    "css",
    "scss",
    "sass",
    "tailwind",
    "styled-components",
    "css-modules",
    "stylesheet",
    "estilos",
    "flexbox",
    "grid",
    "responsive",
    "media query",
    "animation",
    "animación",
    "transition",
    "transición",
    # TypeScript / JavaScript frontend
    "typescript",
    "jsx",
    "tsx",
    "javascript",
    "es6",
    "babel",
    "webpack",
    "vite",
    "rollup",
    "bundler",
    # Testing frontend
    "jest",
    "vitest",
    "cypress",
    "playwright",
    "testing-library",
    "enzyme",
    "unit test frontend",
    "e2e",
    "snapshot",
    # Accesibilidad
    "accessibility",
    "accesibilidad",
    "a11y",
    "wcag",
    "aria",
    "aria-label",
    "aria-role",
    "screen reader",
    "lectura de pantalla",
    # Estado y datos
    "redux",
    "zustand",
    "pinia",
    "vuex",
    "mobx",
    "react-query",
    "tanstack",
    "apollo",
    "graphql frontend",
    "fetch",
    "axios",
    "swr",
    # DOM y navegador
    "dom",
    "browser",
    "navegador",
    "event listener",
    "evento",
    "render",
    "renderizar",
    "hydration",
    "hidratación",
    "ssr",
    "server-side rendering",
    "csr",
    "client-side rendering",
    "ssg",
    "static site generation",
    # UX y UI
    "ui",
    "ux",
    "interfaz",
    "interface",
    "modal",
    "dialog",
    "dropdown",
    "tooltip",
    "notification",
    "notificación",
    "toast",
    "form",
    "formulario",
    "validation",
    "validación",
    "button",
    "botón",
    "input",
    "select",
    "checkbox",
    "radio",
    "toggle",
    "accordion",
    "carousel",
    "slider",
    "navbar",
    "sidebar",
    "footer",
    "header",
    "card",
    "table",
    "tabla",
    "list",
    "lista",
    "menu",
    "tab",
    "tabs",
    "badge",
    "avatar",
    "breadcrumb",
    "pagination",
    "paginación",
    # Router y navegación
    "router",
    "routing",
    "ruta",
    "navegación",
    "navigation",
    "link",
    "enlace",
    "redirect",
    "redirección",
    # Performance frontend
    "lazy load",
    "carga diferida",
    "code splitting",
    "bundle",
    "tree shaking",
    "performance",
    "rendimiento",
    "optimización",
    "optimization",
    "lighthouse",
    "core web vitals",
    "cls",
    "lcp",
    "fid",
    # Build y tooling
    "npm",
    "yarn",
    "pnpm",
    "package.json",
    "tsconfig",
    "eslint",
    "prettier",
    "husky",
    "lint",
    "format",
    "build",
    # Frontend genérico
    "frontend",
    "front-end",
    "front end",
    "web app",
    "aplicación web",
    "spa",
    "single page application",
    "pwa",
    "progressive web app",
    "landing",
    "landing page",
    "dashboard",
    "panel",
    "widget",
]


# =============================================================================
# Frontend Agent
# =============================================================================


class FrontendAgent(AgentBase):
    """
    Agente especializado en desarrollo frontend.

    Este agente maneja tareas relacionadas con:
    - Creación y modificación de componentes UI
    - Implementación de estilos y diseño
    - Desarrollo de lógica del lado del cliente
    - Integración con APIs backend
    - Testing de frontend (unit, e2e, integration)
    - Optimización de rendimiento y bundle
    - Accesibilidad (WCAG)

    Modelo asignado: qwen3-coder-next

    Herramientas disponibles:
        - file_read: Lectura de archivos
        - file_write: Escritura de archivos
        - file_delete: Eliminación de archivos
        - shell_execute: Ejecución de comandos shell
        - npm_install: Instalación de paquetes npm
        - npm_run: Ejecución de scripts npm
        - linter_run: Análisis de código (ESLint, Prettier)
        - test_runner: Ejecución de tests (Jest, Vitest, Cypress)
        - bundle_analyzer: Análisis de bundle
        - a11y_checker: Verificación de accesibilidad
        - browser_preview: Vista previa en navegador
    """

    name: str = "frontend"
    role: AgentRole = AgentRole.FRONTEND
    model: str = "qwen3-coder-next"

    description: str = """
    Agente especializado en desarrollo frontend.

    Puede crear y modificar componentes UI, implementar estilos,
    desarrollar lógica del lado del cliente, integrar con APIs,
    escribir tests, y optimizar rendimiento y accesibilidad.
    """

    system_prompt: str = """
    Eres un agente especializado en desarrollo frontend de clase mundial.

    Tu expertise incluye:
    - Frameworks modernos: React, Vue, Angular, Svelte
    - Lenguajes: TypeScript, JavaScript (ES6+)
    - Estilos: Tailwind CSS, CSS Modules, Styled Components, SASS
    - Build tools: Vite, Webpack, Rollup
    - Testing: Jest, Vitest, React Testing Library, Cypress, Playwright
    - Estado: Redux, Zustand, Pinia, Context API
    - Accesibilidad: WCAG 2.1, aria-*, roles
    - Performance: Code splitting, lazy loading, optimización de bundle

    Principios de diseño:
    1. Componentes reutilizables y componibles
    2. Tipado fuerte con TypeScript
    3. Accesibilidad por defecto
    4. Performance optimizada
    5. Tests comprehensivos
    6. Responsive design
    7. SEO-friendly (cuando aplique)

    Convenciones:
    - Nombres de componentes: PascalCase
    - Nombres de archivos: kebab-case para todo excepto componentes
    - Hooks personalizados: useCamelCase
    - Props: interface con sufijo Props
    - Tests: archivo .test.tsx junto al componente

    Cuando generes código:
    - Incluye tipos TypeScript completos
    - Añade comentarios JSDoc para APIs públicas
    - Implementa manejo de errores
    - Incluye tests unitarios básicos
    - Considera edge cases y estados de loading/error
    - Asegura accesibilidad (aria labels, focus management)

    Responde siempre en el idioma del usuario.
    """

    capabilities: List[AgentCapability] = [
        AgentCapability.FRONTEND_DEVELOPMENT,
        AgentCapability.TESTING,
        AgentCapability.UI_UX_DESIGN,
    ]

    tools: List[str] = [
        "file_read",
        "file_write",
        "file_delete",
        "shell_execute",
        "npm_install",
        "npm_run",
        "linter_run",
        "test_runner",
        "bundle_analyzer",
        "a11y_checker",
        "browser_preview",
    ]

    # Capacidades específicas del agente
    frontend_capabilities: FrontendCapabilities = field(default_factory=FrontendCapabilities)

    # Patrones y frameworks soportados
    supported_frameworks: Dict[str, Dict[str, Any]] = {
        "react": {
            "extension": ".tsx",
            "style_extensions": [".css", ".scss", ".module.css"],
            "test_extension": ".test.tsx",
            "package_manager": "npm",
        },
        "vue": {
            "extension": ".vue",
            "style_extensions": [".css", ".scss"],
            "test_extension": ".test.ts",
            "package_manager": "npm",
        },
        "angular": {
            "extension": ".component.ts",
            "style_extensions": [".scss", ".css"],
            "test_extension": ".spec.ts",
            "package_manager": "npm",
        },
        "svelte": {
            "extension": ".svelte",
            "style_extensions": [".css"],
            "test_extension": ".test.ts",
            "package_manager": "npm",
        },
    }

    # =========================================================================
    # Inicialización
    # =========================================================================

    def __init__(
        self,
        llm_client: "LLMClient",
        capabilities: FrontendCapabilities | None = None,
        tools: list[str] | None = None,
    ):
        """
        Inicializa el agente Frontend.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas del Frontend (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self.frontend_capabilities = capabilities or FrontendCapabilities()
        self._current_framework: Optional[str] = None
        self._styling_framework: Optional[str] = None

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente Frontend.

        Returns:
            Prompt del sistema como cadena
        """
        return self.system_prompt

    def _get_description(self) -> str:
        """
        Obtiene la descripción del agente Frontend.

        Returns:
            Descripción del agente como cadena
        """
        return self.description

    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de desarrollo frontend.

        Flujo de ejecución:
        1. Recuperar contexto relevante de memoria
        2. Analizar la tarea y determinar enfoque
        3. Construir prompt con contexto específico de framework
        4. Invocar LLM
        5. Procesar respuesta y generar artefactos
        6. Guardar aprendizaje en memoria
        7. Retornar resultado

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión con información del proyecto
            memory: Almacén de memoria para contexto adicional

        Returns:
            AgentResult con el resultado de la ejecución
        """
        self.state = AgentState.BUSY
        start_time = datetime.utcnow()

        logger.info(
            "frontend_task_started",
            task_preview=task.description[:100] if task.description else "",
            agent=self.name,
        )

        try:
            # Paso 1: Recuperar contexto relevante de memoria
            relevant_memory = await self._retrieve_relevant_context(
                task=task,
                memory=memory,
            )

            # Paso 2: Construir prompt con contexto
            prompt = self._build_task_prompt(
                task=task,
                context=context,
                memory_context=relevant_memory,
            )

            # Paso 3: Invocar LLM con temperatura moderada para creatividad controlada
            response = await self.invoke_llm(
                prompt=prompt,
                temperature=0.2,  # Temperatura moderada para código preciso pero flexible
            )

            # Paso 4: Procesar respuesta y generar artefactos
            result = self._process_response(response, task)

            # Paso 5: Guardar aprendizaje en memoria si es relevante
            await self._store_learning(
                task=task,
                result=result,
                memory=memory,
            )

            # Actualizar estado
            self.state = AgentState.IDLE

            logger.info(
                "frontend_task_completed",
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
                agent=self.name,
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.exception(
                "frontend_task_failed",
                error=str(e),
                agent=self.name,
            )

            return AgentResult(
                success=False,
                content="",
                errors=[f"Frontend task failed: {str(e)}"],
                metadata={"task": task.description, "agent": self.name},
            )

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Evalúa si la tarea está relacionada con:
        - Desarrollo frontend
        - Componentes UI (React, Vue, Angular, Svelte)
        - Estilos y diseño (CSS, Tailwind, SASS)
        - Lógica del lado del cliente
        - Testing de frontend
        - Accesibilidad
        - Optimización de rendimiento frontend

        Args:
            task: Tarea a evaluar

        Returns:
            True si el agente puede manejar la tarea
        """
        if not task.description:
            return False

        description_lower = task.description.lower()

        # Verificar palabras clave de Frontend
        keyword_matches = sum(1 for keyword in FRONTEND_KEYWORDS if keyword in description_lower)

        # Si hay al menos 2 coincidencias de keywords, probablemente es tarea de Frontend
        if keyword_matches >= 2:
            return True

        # Verificar patrones de componentes/archivos frontend
        frontend_patterns = [
            r"\.tsx\b",
            r"\.jsx\b",
            r"\.vue\b",
            r"\.svelte\b",
            r"\.css\b",
            r"\.scss\b",
            r"\bcomponent\b",
            r"\bimport\s+.*from\s+['\"]react['\"]",
            r"\bimport\s+.*from\s+['\"]vue['\"]",
            r"\bimport\s+.*from\s+['\"]@angular",
            r"\bclassName\s*=",
            r"\bstyle\s*=",
            r"\buseState\b",
            r"\buseEffect\b",
            r"\b<\s*[A-Z]\w+\s",  # JSX component tags
        ]
        for pattern in frontend_patterns:
            if re.search(pattern, description_lower, re.IGNORECASE):
                return True

        # Si solo hay 1 coincidencia, verificar que no sea ambigua
        if keyword_matches == 1:
            # Palabras que por sí solas indican fuertemente tarea de Frontend
            strong_indicators = [
                "react",
                "vue",
                "angular",
                "svelte",
                "nextjs",
                "next.js",
                "nuxt",
                "component",
                "componente",
                "tailwind",
                "css",
                "frontend",
                "front-end",
                "jsx",
                "tsx",
                "typescript",
                "responsive",
                "accesibilidad",
                "accessibility",
                "a11y",
                "wcag",
                "aria",
                "ui",
                "ux",
                "modal",
                "dropdown",
                "tooltip",
                "formulario",
                "form validation",
                "jest",
                "vitest",
                "cypress",
                "playwright",
                "styled-components",
                "css-modules",
                "redux",
                "zustand",
                "pinia",
                "ssr",
                "ssg",
                "spa",
            ]
            for indicator in strong_indicators:
                if indicator in description_lower:
                    return True

        return False

    # =========================================================================
    # Métodos auxiliares del flujo principal
    # =========================================================================

    async def _retrieve_relevant_context(
        self,
        task: Task,
        memory: "MemoryStore",
        max_contexts: int = 5,
    ) -> str:
        """
        Recupera contexto relevante de memoria para la tarea.

        Busca en memoria información relacionada con:
        - Patrones de componentes previos
        - Decisiones de diseño tomadas
        - Configuración de framework
        - Estándares del proyecto

        Args:
            task: Tarea a ejecutar
            memory: Almacén de memoria
            max_contexts: Número máximo de contextos a recuperar

        Returns:
            Contexto formateado como cadena
        """
        try:
            # Recuperar contexto usando el método de la base
            context_str = await self.get_context(
                task=task,
                memory=memory,
                max_contexts=max_contexts,
            )

            # Intentar recuperar contextos específicos de frontend
            frontend_query = SearchQuery(
                query=f"frontend component {task.description}",
                memory_types=[MemoryType.SEMANTIC, MemoryType.EPISODIC],
                top_k=3,
            )

            try:
                frontend_contexts = await memory.search(frontend_query)
                if frontend_contexts:
                    formatted = []
                    for i, ctx in enumerate(frontend_contexts, 1):
                        content = (
                            ctx.get("content", "")
                            if isinstance(ctx, dict)
                            else getattr(ctx, "content", "")
                        )
                        source = (
                            ctx.get("source", "unknown")
                            if isinstance(ctx, dict)
                            else getattr(ctx, "source", "unknown")
                        )
                        formatted.append(f"[{i}] ({source}): {content}")
                    if formatted:
                        context_str = (
                            context_str + "\n\n" + "\n\n".join(formatted)
                            if context_str
                            else "\n\n".join(formatted)
                        )
            except Exception:
                logger.debug(
                    "frontend_search_context_failed",
                    agent=self.name,
                )

            return context_str

        except Exception as e:
            logger.warning(
                "frontend_context_retrieval_failed",
                agent=self.name,
                task_id=task.task_id,
                error=str(e),
            )
            return ""

    def _build_task_prompt(
        self,
        task: Task,
        context: "SessionContext",
        memory_context: str,
    ) -> str:
        """
        Construye el prompt completo para la tarea.

        Combina:
        - Contexto del proyecto (stack, convenciones)
        - Contexto de memoria relevante
        - Framework específico si se detecta
        - Framework de estilos si se detecta
        - La tarea específica
        - Instrucciones de formato

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión
            memory_context: Contexto recuperado de memoria

        Returns:
            Prompt completo para el LLM
        """
        prompt_parts = []

        # Contexto del proyecto
        if hasattr(context, "project_context") and context.project_context:
            project = context.project_context
            if hasattr(project, "config"):
                prompt_parts.append("## Contexto del Proyecto")
                if hasattr(project.config, "name"):
                    prompt_parts.append(f"- Proyecto: {project.config.name}")
                if hasattr(project.config, "stack"):
                    prompt_parts.append(f"- Stack: {project.config.stack}")

        # Contexto de memoria
        if memory_context:
            prompt_parts.append("\n## Contexto Relevante (de memoria)")
            prompt_parts.append(memory_context)

        # Framework específico si se detecta en la descripción
        description_lower = task.description.lower() if task.description else ""
        for framework in self.frontend_capabilities.frameworks:
            if framework in description_lower:
                framework_prompt = self.get_framework_prompt(framework)
                if framework_prompt:
                    prompt_parts.append(f"\n## Instrucciones específicas de {framework.title()}")
                    prompt_parts.append(framework_prompt)
                break

        # Framework de estilos si se detecta
        for styling in self.frontend_capabilities.styling:
            if styling in description_lower:
                styling_instructions = self._get_styling_prompt(styling)
                if styling_instructions:
                    prompt_parts.append(f"\n## Instrucciones de estilos ({styling.title()})")
                    prompt_parts.append(styling_instructions)
                break

        # Tarea
        prompt_parts.append("\n## Tarea")
        prompt_parts.append(task.description)

        # Metadata de la tarea
        if hasattr(task, "metadata") and task.metadata:
            prompt_parts.append("\n## Información Adicional")
            for key, value in task.metadata.items():
                prompt_parts.append(f"- {key}: {value}")

        # Instrucciones de formato
        prompt_parts.append("\n## Instrucciones de Formato")
        prompt_parts.append(
            "Proporciona tu respuesta con el siguiente formato:\n"
            "1. **Enfoque**: Explica tu razonamiento y decisiones de diseño\n"
            "2. **Código**: Implementación completa con TypeScript\n"
            "3. **Estilos**: Estilos CSS/Tailwind necesarios\n"
            "4. **Archivos**: Lista de archivos a crear/modificar\n"
            "5. **Tests**: Tests unitarios y de integración sugeridos\n"
            "6. **Accesibilidad**: Consideraciones de a11y si aplica"
        )

        return "\n".join(prompt_parts)

    def _process_response(
        self,
        response: str,
        task: Task,
    ) -> AgentResult:
        """
        Procesa la respuesta del LLM y genera el resultado.

        Extrae artefactos de la respuesta (código TypeScript/JSX, CSS,
        configs, etc.) y los organiza en el resultado.

        Args:
            response: Respuesta del LLM
            task: Tarea original

        Returns:
            AgentResult con el resultado procesado
        """
        # Extraer bloques de código TypeScript/TSX
        typescript_blocks = self._extract_code_blocks(response, "typescript")
        tsx_blocks = self._extract_code_blocks(response, "tsx")
        jsx_blocks = self._extract_code_blocks(response, "jsx")
        js_blocks = self._extract_code_blocks(response, "javascript")

        # Extraer bloques de estilos
        css_blocks = self._extract_code_blocks(response, "css")
        scss_blocks = self._extract_code_blocks(response, "scss")
        sass_blocks = self._extract_code_blocks(response, "sass")

        # Extraer bloques de configuración
        json_blocks = self._extract_code_blocks(response, "json")
        yaml_blocks = self._extract_code_blocks(response, "yaml")
        toml_blocks = self._extract_code_blocks(response, "toml")

        # Extraer bloques de Vue/Svelte
        vue_blocks = self._extract_code_blocks(response, "vue")
        svelte_blocks = self._extract_code_blocks(response, "svelte")
        html_blocks = self._extract_code_blocks(response, "html")

        # Extraer bloques de shell
        bash_blocks = self._extract_code_blocks(response, "bash")
        shell_blocks = self._extract_code_blocks(response, "shell")

        # Determinar tipo de resultado basado en la tarea
        task_type = self._infer_task_type(task.description)

        # Construir metadata del resultado
        metadata = {
            "agent": self.name,
            "model": self.model,
            "task_type": task_type,
            "typescript_artifacts": len(typescript_blocks) + len(tsx_blocks),
            "javascript_artifacts": len(jsx_blocks) + len(js_blocks),
            "style_artifacts": len(css_blocks) + len(scss_blocks) + len(sass_blocks),
        }

        # Construir lista de artefactos
        artifacts = []

        # Agregar artefactos de código TypeScript/TSX
        for i, block in enumerate(typescript_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "typescript",
                    "content": block,
                    "index": i + 1,
                }
            )

        for i, block in enumerate(tsx_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "tsx",
                    "content": block,
                    "index": i + 1,
                }
            )

        for i, block in enumerate(jsx_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "jsx",
                    "content": block,
                    "index": i + 1,
                }
            )

        for i, block in enumerate(js_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "javascript",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de estilos
        for blocks, lang in [
            (css_blocks, "css"),
            (scss_blocks, "scss"),
            (sass_blocks, "sass"),
        ]:
            for i, block in enumerate(blocks):
                artifacts.append(
                    {
                        "type": "style",
                        "language": lang,
                        "content": block,
                        "index": i + 1,
                    }
                )

        # Agregar artefactos de Vue/Svelte
        for i, block in enumerate(vue_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "vue",
                    "content": block,
                    "index": i + 1,
                }
            )

        for i, block in enumerate(svelte_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "svelte",
                    "content": block,
                    "index": i + 1,
                }
            )

        for i, block in enumerate(html_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": "html",
                    "content": block,
                    "index": i + 1,
                }
            )

        # Agregar artefactos de configuración
        for blocks, lang in [
            (json_blocks, "json"),
            (yaml_blocks, "yaml"),
            (toml_blocks, "toml"),
        ]:
            for i, block in enumerate(blocks):
                artifacts.append(
                    {
                        "type": "config",
                        "language": lang,
                        "content": block,
                        "index": i + 1,
                    }
                )

        # Agregar artefactos de shell
        for blocks, lang in [
            (bash_blocks, "bash"),
            (shell_blocks, "shell"),
        ]:
            for i, block in enumerate(blocks):
                artifacts.append(
                    {
                        "type": "command",
                        "language": lang,
                        "content": block,
                        "index": i + 1,
                    }
                )

        # Agregar metadata de artefactos
        if typescript_blocks or tsx_blocks:
            metadata["typescript_code"] = "[see artifacts]"
        if jsx_blocks or js_blocks:
            metadata["javascript_code"] = "[see artifacts]"
        if css_blocks or scss_blocks or sass_blocks:
            metadata["style_code"] = "[see artifacts]"

        return AgentResult(
            success=True,
            content=response,
            artifacts=artifacts,
            metadata=metadata,
        )

    def _extract_code_blocks(
        self,
        text: str,
        language: str,
    ) -> list[str]:
        """
        Extrae bloques de código de un lenguaje específico.

        Args:
            text: Texto del que extraer bloques
            language: Lenguaje de programación (typescript, css, etc.)

        Returns:
            Lista de bloques de código encontrados
        """
        pattern = rf"```{language}\s*\n(.*?)```"
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return [match.strip() for match in matches]

    def _infer_task_type(self, description: str) -> str:
        """
        Infiere el tipo de tarea basado en la descripción.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de tarea inferido
        """
        description_lower = description.lower()

        type_patterns = {
            "component_creation": [
                "component",
                "componente",
                "widget",
                "ui element",
                "elemento ui",
                "button",
                "botón",
                "modal",
                "dialog",
                "dropdown",
                "tooltip",
                "card",
                "table",
                "tabla",
                "form",
                "formulario",
                "input",
                "select",
                "navbar",
                "sidebar",
                "header",
                "footer",
                "menu",
                "tab",
                "tabs",
                "accordion",
                "carousel",
                "slider",
                "badge",
                "avatar",
                "breadcrumb",
                "pagination",
                "paginación",
            ],
            "page_creation": [
                "page",
                "página",
                "landing",
                "landing page",
                "dashboard",
                "panel",
                "screen",
                "pantalla",
                "view",
                "vista",
            ],
            "styling": [
                "css",
                "scss",
                "sass",
                "tailwind",
                "styled-components",
                "css-modules",
                "estilos",
                "styles",
                "stylesheet",
                "diseño",
                "design",
                "responsive",
                "media query",
                "animation",
                "animación",
                "transition",
                "transición",
                "flexbox",
                "grid",
            ],
            "state_management": [
                "estado",
                "state",
                "redux",
                "zustand",
                "pinia",
                "vuex",
                "mobx",
                "context",
                "provider",
                "usestate",
                "useeffect",
                "usecallback",
                "usememo",
                "useref",
                "hook",
                "hooks",
                "react-query",
                "tanstack",
            ],
            "api_integration": [
                "fetch",
                "axios",
                "api",
                "endpoint",
                "swr",
                "apollo",
                "graphql frontend",
                "rest client",
                "http client",
            ],
            "routing": [
                "router",
                "routing",
                "ruta",
                "navegación",
                "navigation",
                "link",
                "enlace",
                "redirect",
                "redirección",
                "spa",
            ],
            "testing": [
                "jest",
                "vitest",
                "cypress",
                "playwright",
                "testing-library",
                "test",
                "testing",
                "e2e",
                "unit test",
                "test unitario",
                "integration test",
                "test de integración",
                "snapshot",
            ],
            "accessibility": [
                "accessibility",
                "accesibilidad",
                "a11y",
                "wcag",
                "aria",
                "aria-label",
                "aria-role",
                "screen reader",
                "lectura de pantalla",
            ],
            "performance": [
                "lazy load",
                "carga diferida",
                "code splitting",
                "bundle",
                "tree shaking",
                "performance",
                "rendimiento",
                "optimización",
                "optimization",
                "lighthouse",
                "core web vitals",
                "cls",
                "lcp",
                "fid",
                "ssr",
                "server-side rendering",
                "ssg",
                "static site generation",
            ],
            "build_tooling": [
                "webpack",
                "vite",
                "rollup",
                "bundler",
                "npm",
                "yarn",
                "pnpm",
                "package.json",
                "tsconfig",
                "eslint",
                "prettier",
                "husky",
                "lint",
                "format",
                "build",
                "babel",
            ],
        }

        for task_type, keywords in type_patterns.items():
            if any(kw in description_lower for kw in keywords):
                return task_type

        return "general_frontend"

    async def _store_learning(
        self,
        task: Task,
        result: AgentResult,
        memory: "MemoryStore",
    ) -> None:
        """
        Almacena aprendizaje de la tarea en memoria.

        Solo almacena información útil y evita duplicados.

        Args:
            task: Tarea ejecutada
            result: Resultado de la ejecución
            memory: Almacén de memoria
        """
        if not result.success or not result.content:
            return

        try:
            # Determinar tipo de memoria
            memory_type = self._infer_memory_type(task.description)

            # Crear metadata para la memoria
            metadata = {
                "agent": self.name,
                "model": self.model,
                "task_type": self._infer_task_type(task.description),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Almacenar en memoria como conocimiento
            _ = await memory.store_knowledge(
                project_id=task.project_id if hasattr(task, "project_id") else "",
                title=f"Frontend: {task.description[:80]}",
                content=result.content[:1000],  # Limitar tamaño
                tags=[memory_type, self._infer_task_type(task.description)],
                metadata=metadata,
            )

            logger.debug(
                "frontend_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "frontend_learning_store_failed",
                error=str(e),
                agent=self.name,
            )

    def _infer_memory_type(self, description: str) -> str:
        """
        Infiere el tipo de memoria basado en la descripción de la tarea.

        Args:
            description: Descripción de la tarea

        Returns:
            Tipo de memoria inferido
        """
        description_lower = description.lower()

        memory_type_map = {
            "component": "component_pattern",
            "componente": "component_pattern",
            "hook": "hook_pattern",
            "patrón": "design_pattern",
            "pattern": "design_pattern",
            "estilo": "style_pattern",
            "style": "style_pattern",
            "css": "style_pattern",
            "tailwind": "style_pattern",
            "test": "testing_pattern",
            "testing": "testing_pattern",
            "accesibilidad": "a11y_pattern",
            "accessibility": "a11y_pattern",
            "a11y": "a11y_pattern",
            "performance": "performance_pattern",
            "rendimiento": "performance_pattern",
            "optimización": "performance_pattern",
        }

        for keyword, mem_type in memory_type_map.items():
            if keyword in description_lower:
                return mem_type

        return "frontend_general"

    # =========================================================================
    # Métodos de utilidad y dominio
    # =========================================================================

    def detect_framework(self, project_context: Any) -> Optional[str]:
        """
        Detecta el framework frontend del proyecto.

        Busca en:
        - package.json para dependencias
        - Archivos de configuración
        - Estructura de directorios

        Args:
            project_context: Contexto del proyecto

        Returns:
            Nombre del framework detectado o None
        """
        if not project_context:
            return None

        # Intentar detectar desde la configuración del proyecto
        if hasattr(project_context, "config") and project_context.config:
            config = project_context.config
            if hasattr(config, "stack") and config.stack:
                stack_lower = config.stack.lower()
                for framework in self.frontend_capabilities.frameworks:
                    if framework in stack_lower:
                        return framework

        # Intentar detectar desde dependencias del package.json
        if hasattr(project_context, "dependencies") and project_context.dependencies:
            deps = project_context.dependencies
            deps_lower = str(deps).lower()
            if "react" in deps_lower and "next" not in deps_lower:
                return "react"
            if "vue" in deps_lower or "nuxt" in deps_lower:
                return "vue"
            if "angular" in deps_lower or "@angular" in deps_lower:
                return "angular"
            if "svelte" in deps_lower or "sveltekit" in deps_lower:
                return "svelte"
            if "next" in deps_lower:
                return "react"  # Next.js se basa en React

        # Intentar detectar desde archivos del proyecto
        if hasattr(project_context, "files") and project_context.files:
            files_str = str(project_context.files).lower()
            if ".tsx" in files_str or ".jsx" in files_str:
                return "react"
            if ".vue" in files_str:
                return "vue"
            if ".component.ts" in files_str or "angular.json" in files_str:
                return "angular"
            if ".svelte" in files_str:
                return "svelte"

        # Usar el framework actual si está configurado
        return self._current_framework

    def _get_styling_prompt(self, styling: str) -> str:
        """
        Obtiene instrucciones específicas para el framework de estilos.

        Args:
            styling: Nombre del framework de estilos

        Returns:
            Instrucciones de estilos o cadena vacía
        """
        styling_prompts = {
            "tailwind": (
                "Usa Tailwind CSS para los estilos. Sigue estas convenciones:\n"
                "- Usa clases utilitarias de Tailwind directamente en el JSX/HTML\n"
                "- Organiza las clases en orden consistente: "
                "layout → spacing → sizing → typography → colors → effects\n"
                "- Extrae clases repetidas a componentes o @apply\n"
                "- Usa el sistema de diseño de Tailwind (colores, spacing, etc.)\n"
                "- Para estilos complejos, usa la sintaxis de Tailwind arbitraria\n"
                "- Implementa responsive design con los breakpoints de Tailwind"
            ),
            "css-modules": (
                "Usa CSS Modules para los estilos. Sigue estas convenciones:\n"
                "- Archivo [component].module.css junto al componente\n"
                "- Nombres de clases en camelCase\n"
                "- Evita selectores anidados profundos\n"
                "- Usa composición de clases con composes\n"
                "- Importa estilos como styles object"
            ),
            "styled-components": (
                "Usa Styled Components para los estilos. Sigue estas convenciones:\n"
                "- Define componentes estilizados en archivo separado o sección del componente\n"
                "- Usa template literals para estilos dinámicos\n"
                "- Usa el sistema de theming para colores y spacing\n"
                "- Extiende componentes existentes en lugar de duplicar\n"
                "- Nombra componentes estilizados con el prefijo Styled"
            ),
            "sass": (
                "Usa SASS/SCSS para los estilos. Sigue estas convenciones:\n"
                "- Archivo [component].module.scss junto al componente\n"
                "- Usa variables para colores, spacing, tipografía\n"
                "- Anida selectores solo 2-3 niveles\n"
                "- Usa mixins para patrones repetitivos\n"
                "- Organiza con partials y @use/@forward"
            ),
            "emotion": (
                "Usa Emotion para los estilos. Sigue estas convenciones:\n"
                "- Usa la prop css para estilos inline\n"
                "- Define estilos con @emotion/styled para componentes complejos\n"
                "- Usa el sistema de theming para consistencia\n"
                "- Extrae estilos complejos a const separadas"
            ),
        }

        return styling_prompts.get(styling, "")

    def get_framework_prompt(self, framework: str) -> str:
        """
        Obtiene template de instrucciones para el framework.

        Args:
            framework: Framework objetivo

        Returns:
            Instrucciones específicas del framework
        """
        framework_prompts = {
            "react": (
                "Estás trabajando con React. Sigue estas convenciones:\n"
                "- Componentes funcionales con TypeScript\n"
                "- Hooks para estado y efectos\n"
                "- Props tipadas con interfaces\n"
                "- Custom hooks para lógica reutilizable\n"
                "- React.memo para optimización de renders\n"
                "- Manejo de errores con Error Boundaries\n"
                "- Archivos: ComponentName.tsx, ComponentName.module.css, ComponentName.test.tsx"
            ),
            "vue": (
                "Estás trabajando con Vue 3. Sigue estas convenciones:\n"
                "- Composition API con <script setup>\n"
                "- TypeScript en <script lang='ts'>\n"
                "- Props tipadas con defineProps\n"
                "- Emits tipados con defineEmits\n"
                "- Composables para lógica reutilizable\n"
                "- Single File Components (.vue)\n"
                "- Archivos: ComponentName.vue, ComponentName.test.ts"
            ),
            "angular": (
                "Estás trabajando con Angular. Sigue estas convenciones:\n"
                "- Standalone components preferentemente\n"
                "- Signals para estado reactivo\n"
                "- TypeScript estricto\n"
                "- Services para lógica de negocio\n"
                "- RxJS para flujos asíncronos\n"
                "- Archivos: component.ts, component.html, component.scss, component.spec.ts"
            ),
            "svelte": (
                "Estás trabajando con Svelte/SvelteKit. Sigue estas convenciones:\n"
                "- Svelte 5 con runes ($state, $derived, $effect)\n"
                "- TypeScript en <script lang='ts'>\n"
                "- Props tipadas con $props()\n"
                "- Stores para estado global\n"
                "- Server-side rendering con SvelteKit\n"
                "- Archivos: +page.svelte, +page.ts, ComponentName.svelte"
            ),
            "nextjs": (
                "Estás trabajando con Next.js. Sigue estas convenciones:\n"
                "- App Router con server y client components\n"
                "- 'use client' solo cuando sea necesario\n"
                "- Server Components por defecto\n"
                "- Server Actions para mutaciones\n"
                "- Metadata API para SEO\n"
                "- Archivos: page.tsx, layout.tsx, loading.tsx, error.tsx"
            ),
            "nuxt": (
                "Estás trabajando con Nuxt. Sigue estas convenciones:\n"
                "- Auto-imports de componentes y composables\n"
                "- Pages con file-based routing\n"
                "- Server routes en server/api/\n"
                "- Nuxt 3 Composition API\n"
                "- Archivos: pages/, components/, composables/, server/api/"
            ),
            "sveltekit": (
                "Estás trabajando con SvelteKit. Sigue estas convenciones:\n"
                "- File-based routing en src/routes/\n"
                "- Server-side loading con +page.ts\n"
                "- Actions con +page.server.ts\n"
                "- Layouts con +layout.svelte\n"
                "- Archivos: +page.svelte, +page.ts, +layout.svelte"
            ),
        }

        return framework_prompts.get(framework, "")

    async def create_component(
        self,
        component_name: str,
        component_type: str,
        props: Dict[str, Any],
        styles: Optional[str] = None,
        tests: bool = True,
    ) -> Dict[str, Any]:
        """
        Crea un nuevo componente frontend.

        Delega la generación de código al LLM con un prompt estructurado.

        Args:
            component_name: Nombre del componente (PascalCase)
            component_type: Tipo (functional, class, page, layout)
            props: Props del componente
            styles: Framework de estilos (tailwind, css-modules, styled)
            tests: Si debe generar tests

        Returns:
            Diccionario con archivos creados y metadatos
        """
        framework = self._current_framework or "react"
        styling = styles or self._styling_framework or "tailwind"

        # Construir prompt para crear componente
        prompt_parts = [
            f"Create a {component_type} component named {component_name}.",
            f"Framework: {framework}",
            f"Styling: {styling}",
            f"Props: {props}",
        ]

        if tests:
            prompt_parts.append("Include unit tests.")

        prompt = "\n".join(prompt_parts)

        # Invocar LLM para generar el componente
        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.3,
        )

        # Extraer bloques de código de la respuesta
        framework_info = self.supported_frameworks.get(
            framework, self.supported_frameworks["react"]
        )
        extension = framework_info["extension"]

        artifacts = []
        code_blocks = (
            self._extract_code_blocks(response, "typescript")
            + self._extract_code_blocks(response, "tsx")
            + self._extract_code_blocks(response, "javascript")
            + self._extract_code_blocks(response, "jsx")
        )

        for i, block in enumerate(code_blocks):
            artifacts.append(
                {
                    "type": "code",
                    "language": extension.lstrip("."),
                    "content": block,
                    "filename": f"{component_name}{extension}",
                    "index": i + 1,
                }
            )

        style_blocks = self._extract_code_blocks(response, "css") + self._extract_code_blocks(
            response, "scss"
        )

        for i, block in enumerate(style_blocks):
            artifacts.append(
                {
                    "type": "style",
                    "language": "css",
                    "content": block,
                    "filename": f"{component_name}.module.css",
                    "index": i + 1,
                }
            )

        return {
            "component_name": component_name,
            "component_type": component_type,
            "framework": framework,
            "styling": styling,
            "artifacts": artifacts,
            "content": response,
            "files": {
                f"{component_name}{extension}": code_blocks[0] if code_blocks else "",
            },
        }

    async def create_hook(
        self,
        hook_name: str,
        hook_type: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Crea un hook personalizado de React.

        Delega la generación de código al LLM con un prompt estructurado.

        Args:
            hook_name: Nombre del hook (useCamelCase)
            hook_type: Tipo (state, effect, data-fetching, utility)
            parameters: Parámetros del hook

        Returns:
            Diccionario con archivos creados
        """
        prompt_parts = [
            f"Create a custom React hook named {hook_name}.",
            f"Type: {hook_type}",
            f"Parameters: {parameters}",
            "Include TypeScript types.",
            "Include error handling.",
            "Include cleanup if needed.",
            "Include unit tests.",
        ]

        prompt = "\n".join(prompt_parts)

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.3,
        )

        code_blocks = self._extract_code_blocks(response, "typescript") + self._extract_code_blocks(
            response, "tsx"
        )

        return {
            "hook_name": hook_name,
            "hook_type": hook_type,
            "artifacts": [
                {
                    "type": "code",
                    "language": "typescript",
                    "content": block,
                    "filename": f"{hook_name}.ts",
                    "index": i + 1,
                }
                for i, block in enumerate(code_blocks)
            ],
            "content": response,
            "files": {
                f"{hook_name}.ts": code_blocks[0] if code_blocks else "",
            },
        }

    async def create_page(
        self,
        page_name: str,
        route: str,
        layout: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nueva página con routing.

        Delega la generación de código al LLM con un prompt estructurado.

        Args:
            page_name: Nombre de la página
            route: Ruta URL
            layout: Layout a usar
            metadata: Metadatos SEO

        Returns:
            Diccionario con archivos creados
        """
        framework = self._current_framework or "react"

        prompt_parts = [
            f"Create a page component named {page_name}.",
            f"Route: {route}",
            f"Framework: {framework}",
        ]

        if layout:
            prompt_parts.append(f"Layout: {layout}")
        if metadata:
            prompt_parts.append(f"SEO metadata: {metadata}")

        prompt_parts.extend(
            [
                "Include TypeScript types.",
                "Include loading and error states.",
                "Include accessibility considerations.",
            ]
        )

        prompt = "\n".join(prompt_parts)

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.3,
        )

        code_blocks = self._extract_code_blocks(response, "typescript") + self._extract_code_blocks(
            response, "tsx"
        )

        return {
            "page_name": page_name,
            "route": route,
            "framework": framework,
            "artifacts": [
                {
                    "type": "code",
                    "language": "typescript",
                    "content": block,
                    "index": i + 1,
                }
                for i, block in enumerate(code_blocks)
            ],
            "content": response,
        }

    async def create_api_client(
        self,
        api_name: str,
        base_url: str,
        endpoints: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Crea un cliente API para comunicación con backend.

        Delega la generación de código al LLM con un prompt estructurado.

        Args:
            api_name: Nombre del cliente API
            base_url: URL base del API
            endpoints: Lista de endpoints

        Returns:
            Diccionario con archivos creados
        """
        prompt_parts = [
            f"Create an API client named {api_name}.",
            f"Base URL: {base_url}",
            f"Endpoints: {endpoints}",
            "Use TypeScript with proper types.",
            "Include error handling.",
            "Include request/response types.",
            "Include retry logic.",
        ]

        prompt = "\n".join(prompt_parts)

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.2,
        )

        code_blocks = self._extract_code_blocks(response, "typescript")

        return {
            "api_name": api_name,
            "base_url": base_url,
            "artifacts": [
                {
                    "type": "code",
                    "language": "typescript",
                    "content": block,
                    "index": i + 1,
                }
                for i, block in enumerate(code_blocks)
            ],
            "content": response,
        }

    async def optimize_bundle(
        self,
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Optimiza el bundle del frontend.

        Delega el análisis y recomendaciones al LLM.

        Args:
            analysis: Análisis del bundle actual

        Returns:
            Recomendaciones y cambios aplicados
        """
        prompt_parts = [
            "Analyze and provide optimization recommendations for the following frontend bundle:",
            f"Bundle analysis: {analysis}",
            "Consider: code splitting, tree shaking, lazy loading, compression.",
            "Provide specific, actionable recommendations with code examples.",
        ]

        prompt = "\n".join(prompt_parts)

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.2,
        )

        return {
            "analysis": analysis,
            "recommendations": response,
            "artifacts": self._extract_code_blocks(response, "typescript")
            + self._extract_code_blocks(response, "javascript"),
        }

    async def run_linter(
        self,
        files: Optional[List[str]] = None,
        fix: bool = False,
    ) -> Dict[str, Any]:
        """
        Ejecuta el linter en archivos frontend.

        Proporciona recomendaciones de linting basadas en el contexto.

        Args:
            files: Lista de archivos (None = todos)
            fix: Si debe auto-corregir

        Returns:
            Resultado del linter con errores y warnings
        """
        scope = f"Files: {', '.join(files)}" if files else "All project files"

        prompt = (
            f"Review the following frontend code for linting issues: {scope}. "
            f"Auto-fix: {'Yes' if fix else 'No'}. "
            "Provide specific issues found and suggested fixes."
        )

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.1,
        )

        return {
            "files": files,
            "fix": fix,
            "result": response,
            "errors": [],
            "warnings": [],
        }

    async def run_tests(
        self,
        test_type: str = "unit",
        files: Optional[List[str]] = None,
        coverage: bool = True,
    ) -> Dict[str, Any]:
        """
        Ejecuta tests de frontend.

        Genera recomendaciones de testing basadas en el contexto.

        Args:
            test_type: Tipo de test (unit, e2e, integration)
            files: Archivos específicos (None = todos)
            coverage: Si debe generar reporte de coverage

        Returns:
            Resultado de tests con coverage
        """
        scope = f"Files: {', '.join(files)}" if files else "All project files"

        prompt = (
            f"Generate {test_type} tests for frontend code: {scope}. "
            f"Coverage report: {'Yes' if coverage else 'No'}. "
            "Provide complete test code with proper assertions and mocking."
        )

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.2,
        )

        code_blocks = self._extract_code_blocks(response, "typescript") + self._extract_code_blocks(
            response, "tsx"
        )

        return {
            "test_type": test_type,
            "files": files,
            "coverage": coverage,
            "result": response,
            "test_artifacts": code_blocks,
        }

    async def check_accessibility(
        self,
        component: str,
        wcag_level: str = "AA",
    ) -> Dict[str, Any]:
        """
        Verifica accesibilidad del componente.

        Delega el análisis de accesibilidad al LLM.

        Args:
            component: Nombre del componente
            wcag_level: Nivel WCAG (A, AA, AAA)

        Returns:
            Reporte de accesibilidad
        """
        prompt = (
            f"Review the component '{component}' for accessibility issues "
            f"at WCAG {wcag_level} level. "
            "Check: aria attributes, semantic HTML, focus management, "
            "color contrast, keyboard navigation, screen reader compatibility. "
            "Provide specific issues and fixes."
        )

        response = await self.invoke_llm(
            prompt=prompt,
            temperature=0.1,
        )

        return {
            "component": component,
            "wcag_level": wcag_level,
            "report": response,
        }

    def get_component_template(
        self,
        framework: str,
        component_type: str,
        styling: str = "tailwind",
    ) -> str:
        """
        Obtiene template de componente para el framework.

        Args:
            framework: Framework objetivo
            component_type: Tipo de componente
            styling: Framework de estilos

        Returns:
            Template del componente
        """
        templates = {
            "react": {
                "functional": self._get_react_functional_template(styling),
                "page": self._get_react_page_template(styling),
            },
            "vue": {
                "functional": self._get_vue_functional_template(styling),
                "page": self._get_vue_page_template(styling),
            },
            "angular": {
                "functional": self._get_angular_component_template(styling),
                "page": self._get_angular_page_template(styling),
            },
            "svelte": {
                "functional": self._get_svelte_functional_template(styling),
                "page": self._get_svelte_page_template(styling),
            },
        }

        framework_templates = templates.get(framework, templates.get("react", {}))
        return framework_templates.get(component_type, framework_templates.get("functional", ""))

    def get_test_template(
        self,
        framework: str,
        test_type: str = "unit",
    ) -> str:
        """
        Obtiene template de test para el framework.

        Args:
            framework: Framework objetivo
            test_type: Tipo de test

        Returns:
            Template del test
        """
        test_templates = {
            "react": {
                "unit": "// ComponentName.test.tsx\nimport { render, screen } from '@testing-library/react';\nimport ComponentName from './ComponentName';\n\ndescribe('ComponentName', () => {\n  it('renders correctly', () => {\n    render(<ComponentName />);\n    expect(screen.getByText(/expected text/i)).toBeInTheDocument();\n  });\n});\n",
                "e2e": "// ComponentName.e2e.ts\nimport { test, expect } from '@playwright/test';\n\ntest('ComponentName renders correctly', async ({ page }) => {\n  await page.goto('/route');\n  await expect(page.getByText('Expected Text')).toBeVisible();\n});\n",
            },
            "vue": {
                "unit": "// ComponentName.test.ts\nimport { mount } from '@vue/test-utils';\nimport ComponentName from './ComponentName.vue';\n\ndescribe('ComponentName', () => {\n  it('renders correctly', () => {\n    const wrapper = mount(ComponentName);\n    expect(wrapper.text()).toContain('expected text');\n  });\n});\n",
                "e2e": "// ComponentName.e2e.ts\nimport { test, expect } from '@playwright/test';\n\ntest('ComponentName renders correctly', async ({ page }) => {\n  await page.goto('/route');\n  await expect(page.getByText('Expected Text')).toBeVisible();\n});\n",
            },
        }

        framework_tests = test_templates.get(framework, test_templates.get("react", {}))
        return framework_tests.get(test_type, framework_tests.get("unit", ""))

    # =========================================================================
    # Templates internos de componentes
    # =========================================================================

    def _get_react_functional_template(self, styling: str = "tailwind") -> str:
        """Template de componente funcional React."""
        if styling == "tailwind":
            return (
                "import { type FC, type ReactNode } from 'react';\n\n"
                "interface ComponentNameProps {\n"
                "  children?: ReactNode;\n"
                "  className?: string;\n"
                "}\n\n"
                "const ComponentName: FC<ComponentNameProps> = ({\n"
                "  children,\n"
                "  className = '',\n"
                "}) => {\n"
                "  return (\n"
                "    <div className={className}>\n"
                "      {children}\n"
                "    </div>\n"
                "  );\n"
                "};\n\n"
                "export default ComponentName;\n"
            )
        return (
            "import { type FC, type ReactNode } from 'react';\n"
            "import styles from './ComponentName.module.css';\n\n"
            "interface ComponentNameProps {\n"
            "  children?: ReactNode;\n"
            "  className?: string;\n"
            "}\n\n"
            "const ComponentName: FC<ComponentNameProps> = ({\n"
            "  children,\n"
            "  className = '',\n"
            "}) => {\n"
            "  return (\n"
            "    <div className={`${styles.container} ${className}`}>\n"
            "      {children}\n"
            "    </div>\n"
            "  );\n"
            "};\n\n"
            "export default ComponentName;\n"
        )

    def _get_react_page_template(self, styling: str = "tailwind") -> str:
        """Template de página React."""
        return (
            "import { type FC } from 'react';\n\n"
            "interface PageNameProps {\n"
            "  // Add page-level props here\n"
            "}\n\n"
            "const PageName: FC<PageNameProps> = () => {\n"
            "  return (\n"
            "    <main>\n"
            "      <h1>Page Title</h1>\n"
            "      <p>Page content goes here</p>\n"
            "    </main>\n"
            "  );\n"
            "};\n\n"
            "export default PageName;\n"
        )

    def _get_vue_functional_template(self, styling: str = "tailwind") -> str:
        """Template de componente funcional Vue."""
        if styling == "tailwind":
            return (
                "<script setup lang='ts'>\n"
                "interface Props {\n"
                "  title?: string\n"
                "  className?: string\n"
                "}\n\n"
                "const props = withDefaults(defineProps<Props>(), {\n"
                "  title: '',\n"
                "  className: '',\n"
                "})\n"
                "</script>\n\n"
                "<template>\n"
                '  <div :class="props.className">\n'
                "    <h2>{{ props.title }}</h2>\n"
                "    <slot />\n"
                "  </div>\n"
                "</template>\n"
            )
        return (
            "<script setup lang='ts'>\n"
            "interface Props {\n"
            "  title?: string\n"
            "  className?: string\n"
            "}\n\n"
            "const props = withDefaults(defineProps<Props>(), {\n"
            "  title: '',\n"
            "  className: '',\n"
            "})\n"
            "</script>\n\n"
            "<style module scoped>\n"
            ".container {\n"
            "  padding: 1rem;\n"
            "}\n"
            "</style>\n\n"
            "<template>\n"
            '  <div :class="[$style.container, props.className]">\n'
            "    <h2>{{ props.title }}</h2>\n"
            "    <slot />\n"
            "  </div>\n"
            "</template>\n"
        )

    def _get_vue_page_template(self, styling: str = "tailwind") -> str:
        """Template de página Vue."""
        return (
            "<script setup lang='ts'>\n"
            "// Page-level logic here\n"
            "</script>\n\n"
            "<template>\n"
            "  <main>\n"
            "    <h1>Page Title</h1>\n"
            "    <p>Page content goes here</p>\n"
            "  </main>\n"
            "</template>\n"
        )

    def _get_angular_component_template(self, styling: str = "tailwind") -> str:
        """Template de componente Angular."""
        return (
            "import { Component, Input } from '@angular/core';\n\n"
            "@Component({\n"
            "  selector: 'app-component-name',\n"
            "  standalone: true,\n"
            "  template: `\n"
            "    <div>\n"
            "      <h2>{{ title }}</h2>\n"
            "      <ng-content></ng-content>\n"
            "    </div>\n"
            "  `,\n"
            "})\n"
            "export class ComponentNameComponent {\n"
            "  @Input() title = '';\n"
            "}\n"
        )

    def _get_angular_page_template(self, styling: str = "tailwind") -> str:
        """Template de página Angular."""
        return (
            "import { Component } from '@angular/core';\n\n"
            "@Component({\n"
            "  selector: 'app-page-name',\n"
            "  standalone: true,\n"
            "  template: `\n"
            "    <main>\n"
            "      <h1>Page Title</h1>\n"
            "      <p>Page content goes here</p>\n"
            "    </main>\n"
            "  `,\n"
            "})\n"
            "export class PageNameComponent {}\n"
        )

    def _get_svelte_functional_template(self, styling: str = "tailwind") -> str:
        """Template de componente funcional Svelte."""
        if styling == "tailwind":
            return (
                "<script lang='ts'>\n"
                "interface Props {\n"
                "  title?: string;\n"
                "  className?: string;\n"
                "}\n\n"
                "let { title = '', className = '' }: Props = $props();\n"
                "</script>\n\n"
                "<div class={className}>\n"
                "  <h2>{title}</h2>\n"
                "  {@render children()}\n"
                "</div>\n"
            )
        return (
            "<script lang='ts'>\n"
            "interface Props {\n"
            "  title?: string;\n"
            "  className?: string;\n"
            "}\n\n"
            "let { title = '', className = '' }: Props = $props();\n"
            "</script>\n\n"
            "<style>\n"
            ".container {\n"
            "  padding: 1rem;\n"
            "}\n"
            "</style>\n\n"
            "<div class='container {className}'>\n"
            "  <h2>{title}</h2>\n"
            "  {@render children()}\n"
            "</div>\n"
        )

    def _get_svelte_page_template(self, styling: str = "tailwind") -> str:
        """Template de página Svelte."""
        return (
            "<script lang='ts'>\n"
            "// Page-level logic here\n"
            "</script>\n\n"
            "<main>\n"
            "  <h1>Page Title</h1>\n"
            "  <p>Page content goes here</p>\n"
            "</main>\n"
        )
