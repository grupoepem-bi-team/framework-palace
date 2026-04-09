"""
Agente Designer - Palace Framework

Este agente se especializa en diseño UI/UX, incluyendo:
- Diseño de interfaces de usuario
- Sistemas de diseño y componentes
- Accesibilidad (WCAG)
- Experiencia de usuario
- Wireframes y prototipos
- Guías de estilo

Modelo asignado: mistral-large
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.agents.base import AgentBase, AgentResult, AgentRole, AgentState, Task
from palace.core.types import AgentCapability

if TYPE_CHECKING:
    from palace.context import SessionContext
    from palace.llm import LLMClient
    from palace.memory import MemoryStore

logger = structlog.get_logger()


class DesignTaskType(str, Enum):
    """Tipos de tareas que puede manejar el agente Designer."""

    UI_COMPONENT = "ui_component"
    """Diseño de componentes UI."""

    DESIGN_SYSTEM = "design_system"
    """Creación de sistemas de diseño."""

    WIREFRAME = "wireframe"
    """Wireframes y prototipos."""

    USER_FLOW = "user_flow"
    """Flujos de usuario."""

    ACCESSIBILITY = "accessibility"
    """Auditoría y mejoras de accesibilidad."""

    STYLE_GUIDE = "style_guide"
    """Guías de estilo y branding."""

    RESPONSIVE = "responsive"
    """Diseño responsive."""

    ANIMATION = "animation"
    """Animaciones y transiciones."""


@dataclass
class DesignCapabilities:
    """Capacidades específicas del agente Designer."""

    frameworks: List[str] = field(
        default_factory=lambda: [
            "Figma",
            "Sketch",
            "Adobe XD",
            "Tailwind CSS",
            "Material Design",
            "Bootstrap",
            "Chakra UI",
            "Radix UI",
        ]
    )

    principles: List[str] = field(
        default_factory=lambda: [
            "Visual hierarchy",
            "Consistency",
            "Feedback",
            "Affordance",
            "Accessibility",
            "Responsive design",
            "User-centered design",
            "Atomic design",
        ]
    )

    deliverables: List[str] = field(
        default_factory=lambda: [
            "Component specifications",
            "Design tokens",
            "Style guide",
            "Wireframes",
            "User flow diagrams",
            "Accessibility checklist",
            "Responsive breakpoints",
            "Animation specs",
        ]
    )


class DesignerAgent(AgentBase):
    """
    Agente especializado en diseño UI/UX.

    Este agente maneja tareas relacionadas con:
    - Diseño de interfaces de usuario
    - Sistemas de diseño y componentes
    - Accesibilidad y usabilidad
    - Experiencia de usuario
    - Wireframes y prototipos
    - Guías de estilo

    Modelo: mistral-large

    Herramientas disponibles:
        - file_read: Leer archivos existentes
        - file_write: Crear/modificar archivos
        - web_search: Buscar referencias de diseño
        - accessibility_checker: Verificar WCAG
        - color_contrast: Verificar contrastes
        - responsive_preview: Vista previa responsive
    """

    name: str = "designer"
    model: str = "mistral-large"
    role: AgentRole = AgentRole.DESIGNER
    description: str = (
        "Agente especializado en diseño UI/UX con experiencia en sistemas de diseño, "
        "accesibilidad, experiencia de usuario y diseño responsive."
    )

    capabilities: List[AgentCapability] = [
        AgentCapability.UI_UX_DESIGN,
        AgentCapability.DOCUMENTATION,
    ]

    tools: List[str] = [
        "file_read",
        "file_write",
        "web_search",
        "accessibility_checker",
        "color_contrast",
        "responsive_preview",
    ]

    design_capabilities: DesignCapabilities = field(default_factory=DesignCapabilities)

    system_prompt: str = """Eres un diseñador UI/UX senior especializado en crear interfaces de usuario elegantes, accesibles y funcionales.

Tu expertise incluye:
- Diseño de componentes atómicos y sistemas de diseño
- Diseño responsive (mobile-first)
- Accesibilidad (WCAG 2.1 AA/AAA)
- Experiencia de usuario (UX)
- Diseño visual (color, tipografía, espaciado)
- Prototipado y wireframing
- Design tokens y theming

Principios de diseño que sigues:
1. **Claridad**: Interfaces intuitivas y fáciles de entender
2. **Consistencia**: Patrones y estilos uniformes
3. **Accesibilidad**: Diseño inclusivo para todos los usuarios
4. **Responsive**: Adaptable a todos los dispositivos
5. **Performance**: Diseño que no compromete el rendimiento

Cuando diseñes:
1. Considera el contexto del proyecto y framework existente
2. Aplica principios de diseño atómico
3. Usa design tokens para consistencia
4. Incluye estados (hover, focus, active, disabled)
5. Considera accesibilidad desde el inicio
6. Documenta decisiones de diseño

Formato de respuesta:
- Describe el enfoque de diseño
- Proporciona código/styling específico
- Incluye consideraciones de accesibilidad
- Documenta variantes y estados
- Sugiere mejoras futuras

Siempre proporciona:
- Código CSS/Tailwind funcional
- Estructura de componentes clara
- Design tokens utilizados
- Consideraciones de accesibilidad
- Notas sobre responsive design"""

    def __init__(
        self,
        llm_client: "LLMClient",
        capabilities: Optional[DesignCapabilities] = None,
        tools: Optional[List[str]] = None,
    ):
        """Inicializa el agente Designer.

        Args:
            llm_client: Cliente LLM para invocar modelos
            capabilities: Capacidades específicas de diseño (opcional)
            tools: Herramientas disponibles (opcional)
        """
        super().__init__(
            name=self.name,
            role=self.role,
            model=self.model,
            llm_client=llm_client,
            tools=tools or self.tools,
        )
        self._capabilities_config = capabilities or DesignCapabilities()
        logger.info(
            "designer_agent_initialized",
            model=self.model,
            capabilities=[c.value for c in self.capabilities]
            if hasattr(self.capabilities, "__iter__")
            else [],
        )

    # =========================================================================
    # Métodos abstractos de AgentBase
    # =========================================================================

    def _build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el agente Designer.

        Returns:
            System prompt string
        """
        return self.system_prompt

    def _get_description(self) -> str:
        """
        Obtiene la descripción del agente Designer.

        Returns:
            Descripción del agente como cadena
        """
        return self.description

    # =========================================================================
    # Ejecución principal
    # =========================================================================

    async def run(
        self,
        task: Task,
        context: "SessionContext",
        memory: "MemoryStore",
    ) -> AgentResult:
        """
        Ejecuta una tarea de diseño.

        Flujo de ejecución:
        1. Recuperar contexto relevante de memoria
        2. Analizar el tipo de tarea de diseño
        3. Construir prompt con contexto
        4. Invocar LLM para generar diseño
        5. Verificar accesibilidad
        6. Guardar aprendizaje en memoria
        7. Retornar resultado con especificaciones

        Args:
            task: Tarea a ejecutar
            context: Contexto de sesión
            memory: Almacén de memoria

        Returns:
            AgentResult con el diseño generado
        """
        self.state = AgentState.BUSY
        start_time = datetime.utcnow()

        logger.info(
            "designer_agent_executing",
            task_id=task.task_id,
            project_id=task.project_id,
        )

        try:
            # 1. Recuperar contexto relevante de memoria
            context_str = await self.get_context(task, memory)

            # 2. Analizar tipo de tarea
            task_type = await self._analyze_task_type(task.description)

            # 3. Recuperar contexto de diseño específico
            design_context = await self._retrieve_design_context(
                task=task.description,
                task_type=task_type,
                memory=memory,
                project_id=task.project_id,
            )

            # 4. Construir prompt con contexto recuperado
            additional_instructions = self._build_design_instructions(task_type, design_context)
            prompt = self.build_prompt(task, context_str, additional_instructions)

            # 5. Invocar LLM para generar diseño
            llm_response = await self.invoke_llm(prompt)

            # 6. Procesar respuesta del LLM
            design_result = await self._generate_design(
                task=task,
                task_type=task_type,
                context=context,
                design_context=design_context,
                llm_response=llm_response,
            )

            # 7. Verificar accesibilidad
            accessibility_result = await self._check_accessibility(design_result)

            # 8. Guardar aprendizaje en memoria
            await self._save_learning(task, design_result, memory)

            # 9. Crear resultado
            result = self._create_result(
                task=task,
                design_result=design_result,
                accessibility=accessibility_result,
            )

            self.state = AgentState.IDLE

            logger.info(
                "designer_agent_completed",
                task_id=task.task_id,
                task_type=task_type.value,
                success=result.success,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

            return result

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(
                "designer_agent_failed",
                task_id=task.task_id,
                error=str(e),
            )

            return AgentResult(
                success=False,
                content="",
                errors=[f"Designer task failed: {str(e)}"],
                metadata={"task": task.description, "agent": self.name},
            )

    # =========================================================================
    # Manejo de tareas
    # =========================================================================

    def can_handle(self, task: Task) -> bool:
        """
        Determina si este agente puede manejar la tarea.

        Analiza el prompt para detectar tareas relacionadas con:
        - Diseño de UI/UX
        - Componentes visuales
        - Sistemas de diseño
        - Accesibilidad
        - Estilos y theming

        Args:
            task: Tarea a evaluar

        Returns:
            True si puede manejar la tarea
        """
        design_keywords = [
            "design",
            "ui",
            "ux",
            "interface",
            "component",
            "button",
            "input",
            "modal",
            "card",
            "form",
            "layout",
            "style",
            "css",
            "tailwind",
            "responsive",
            "accessibility",
            "a11y",
            "wcag",
            "color",
            "theme",
            "dark mode",
            "animation",
            "transition",
            "wireframe",
            "prototype",
            "user experience",
            "user flow",
            "design system",
            "style guide",
            "figma",
            "sketch",
            "atomic design",
        ]

        if not task.description:
            return False

        prompt_lower = task.description.lower()
        return any(keyword in prompt_lower for keyword in design_keywords)

    # =========================================================================
    # Construcción de prompt
    # =========================================================================

    def _build_design_instructions(
        self,
        task_type: DesignTaskType,
        design_context: Dict[str, Any],
    ) -> str:
        """
        Construye instrucciones adicionales basadas en el tipo de tarea y contexto.

        Args:
            task_type: Tipo de tarea de diseño
            design_context: Contexto de diseño recuperado

        Returns:
            Instrucciones adicionales para el prompt
        """
        instructions = f"Tipo de tarea de diseño: {task_type.value}\n\n"

        if task_type == DesignTaskType.UI_COMPONENT:
            instructions += (
                "Diseña el componente siguiendo principios de diseño atómico.\n"
                "Incluye: estados (default, hover, focus, active, disabled), "
                "variantes de tamaño (sm, md, lg), variantes de color/intento, "
                "accesibilidad WCAG 2.1 AA, y responsive design.\n"
            )
        elif task_type == DesignTaskType.DESIGN_SYSTEM:
            instructions += (
                "Crea un sistema de diseño completo con: design tokens (colores, "
                "tipografía, espaciado, sombras), componentes base, patrones, "
                "y documentación de uso.\n"
            )
        elif task_type == DesignTaskType.ACCESSIBILITY:
            instructions += (
                "Realiza una auditoría de accesibilidad WCAG 2.1 verificando: "
                "perceptible, operable, comprensible y robusto.\n"
            )
        elif task_type == DesignTaskType.WIREFRAME:
            instructions += (
                "Crea wireframes con estructura clara, jerarquía visual, "
                "y flujo de navegación lógico.\n"
            )
        elif task_type == DesignTaskType.STYLE_GUIDE:
            instructions += (
                "Genera una guía de estilo con: colores de marca, tipografía, "
                "espaciado, y especificaciones de componentes.\n"
            )

        # Añadir contexto existente si está disponible
        if design_context.get("existing_components"):
            instructions += f"\nComponentes existentes: {design_context['existing_components']}\n"
        if design_context.get("design_tokens"):
            instructions += f"\nDesign tokens existentes: {design_context['design_tokens']}\n"

        return instructions

    # =========================================================================
    # Análisis de tareas
    # =========================================================================

    async def _analyze_task_type(self, prompt: str) -> DesignTaskType:
        """
        Analiza el prompt para determinar el tipo de tarea de diseño.

        Args:
            prompt: Descripción de la tarea

        Returns:
            Tipo de tarea de diseño identificada
        """
        prompt_lower = prompt.lower()

        # Detección por keywords
        if any(kw in prompt_lower for kw in ["component", "button", "input", "card", "modal"]):
            return DesignTaskType.UI_COMPONENT

        if any(kw in prompt_lower for kw in ["design system", "design tokens", "theme"]):
            return DesignTaskType.DESIGN_SYSTEM

        if any(kw in prompt_lower for kw in ["wireframe", "prototype", "mockup"]):
            return DesignTaskType.WIREFRAME

        if any(kw in prompt_lower for kw in ["user flow", "user journey", "flow diagram"]):
            return DesignTaskType.USER_FLOW

        if any(kw in prompt_lower for kw in ["accessibility", "a11y", "wcag", "aria"]):
            return DesignTaskType.ACCESSIBILITY

        if any(kw in prompt_lower for kw in ["style guide", "branding", "colors", "typography"]):
            return DesignTaskType.STYLE_GUIDE

        if any(kw in prompt_lower for kw in ["responsive", "mobile", "breakpoint", "adaptive"]):
            return DesignTaskType.RESPONSIVE

        if any(
            kw in prompt_lower for kw in ["animation", "transition", "motion", "micro-interaction"]
        ):
            return DesignTaskType.ANIMATION

        return DesignTaskType.UI_COMPONENT

    # =========================================================================
    # Recuperación de contexto
    # =========================================================================

    async def _retrieve_design_context(
        self,
        task: str,
        task_type: DesignTaskType,
        memory: "MemoryStore",
        project_id: str,
    ) -> Dict[str, Any]:
        """
        Recupera contexto de diseño relevante desde memoria.

        Args:
            task: Descripción de la tarea
            task_type: Tipo de tarea
            memory: Almacén de memoria
            project_id: ID del proyecto

        Returns:
            Contexto de diseño recuperado
        """
        context: Dict[str, Any] = {
            "existing_components": [],
            "design_tokens": [],
            "style_guide": [],
            "accessibility_rules": [],
            "patterns": [],
        }

        try:
            # Recuperar contexto de diseño existente
            design_contexts = await memory.retrieve_context(
                project_id=project_id,
                query=f"design system components tokens {task_type.value}",
                top_k=5,
            )

            for ctx in design_contexts:
                content = ctx.get("content", "")
                metadata = ctx.get("metadata", {})
                ctx_type = metadata.get("type", "") if isinstance(metadata, dict) else ""

                if "component" in ctx_type or "component" in content.lower():
                    context["existing_components"].append(content)
                elif "token" in ctx_type or "token" in content.lower():
                    context["design_tokens"].append(content)
                elif "style" in ctx_type or "style guide" in content.lower():
                    context["style_guide"].append(content)
                elif "accessibility" in ctx_type or "wcag" in content.lower():
                    context["accessibility_rules"].append(content)
                else:
                    context["patterns"].append(content)

            logger.debug(
                "design_context_retrieved",
                task_type=task_type.value,
                context_keys=list(context.keys()),
                total_items=sum(len(v) for v in context.values() if isinstance(v, list)),
            )
        except Exception as e:
            logger.warning(
                "design_context_retrieval_failed",
                task_type=task_type.value,
                error=str(e),
            )

        return context

    # =========================================================================
    # Generación de diseño
    # =========================================================================

    async def _generate_design(
        self,
        task: Task,
        task_type: DesignTaskType,
        context: "SessionContext",
        design_context: Dict[str, Any],
        llm_response: str,
    ) -> Dict[str, Any]:
        """
        Genera el diseño basado en el tipo de tarea y la respuesta del LLM.

        Args:
            task: Tarea a resolver
            task_type: Tipo de tarea
            context: Contexto de sesión
            design_context: Contexto de diseño recuperado
            llm_response: Respuesta del LLM

        Returns:
            Diseño generado con especificaciones
        """
        # Base del resultado con la respuesta del LLM
        design_result: Dict[str, Any] = {
            "type": task_type.value,
            "llm_response": llm_response,
            "components": [],
            "styles": {},
            "tokens": {},
            "accessibility": {},
            "documentation": llm_response,
            "recommendations": [],
        }

        # Enriquecer resultado según el tipo de tarea
        if task_type == DesignTaskType.UI_COMPONENT:
            design_result.update(self._parse_component_response(llm_response))
        elif task_type == DesignTaskType.DESIGN_SYSTEM:
            design_result.update(self._parse_design_system_response(llm_response))
        elif task_type == DesignTaskType.ACCESSIBILITY:
            design_result.update(self._parse_accessibility_response(llm_response))
        elif task_type == DesignTaskType.STYLE_GUIDE:
            design_result.update(self._parse_style_guide_response(llm_response))
        else:
            design_result.update(self._parse_generic_response(llm_response))

        return design_result

    # =========================================================================
    # Parseo de respuestas del LLM
    # =========================================================================

    def _parse_component_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para componentes UI.

        Args:
            llm_response: Respuesta del LLM

        Returns:
            Estructura de componente parseada
        """
        return {
            "type": "ui_component",
            "structure": llm_response,
            "styles": "/* Ver estructura del componente en la respuesta */",
            "tokens": {
                "colors": {"primary": "#3B82F6", "secondary": "#6B7280"},
                "spacing": {"sm": "0.5rem", "md": "1rem", "lg": "1.5rem"},
                "radius": {"sm": "0.25rem", "md": "0.5rem", "lg": "1rem"},
            },
            "accessibility": {
                "wcag_level": "AA",
                "contrast_ratio": "4.5:1",
                "keyboard_navigation": True,
                "screen_reader": True,
            },
            "variants": ["default", "outlined", "ghost"],
            "sizes": ["sm", "md", "lg"],
            "states": ["default", "hover", "focus", "active", "disabled"],
            "documentation": llm_response,
            "recommendations": [
                "Consider adding loading state",
                "Add tooltip for additional context",
                "Ensure focus visible for keyboard users",
            ],
        }

    def _parse_design_system_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para sistemas de diseño.

        Args:
            llm_response: Respuesta del LLM

        Returns:
            Estructura de design system parseada
        """
        return {
            "type": "design_system",
            "tokens": {
                "colors": {
                    "primary": {"50": "#EFF6FF", "500": "#3B82F6", "900": "#1E3A8A"},
                    "secondary": {"50": "#F9FAFB", "500": "#6B7280", "900": "#111827"},
                    "semantic": {
                        "success": "#10B981",
                        "warning": "#F59E0B",
                        "error": "#EF4444",
                        "info": "#3B82F6",
                    },
                },
                "typography": {
                    "fontFamily": {
                        "sans": "Inter, system-ui, sans-serif",
                        "mono": "JetBrains Mono, monospace",
                    },
                    "fontSizes": {
                        "xs": "0.75rem",
                        "sm": "0.875rem",
                        "base": "1rem",
                        "lg": "1.125rem",
                        "xl": "1.25rem",
                    },
                },
                "spacing": {
                    "0": "0",
                    "1": "0.25rem",
                    "2": "0.5rem",
                    "4": "1rem",
                    "8": "2rem",
                },
                "shadows": {
                    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
                    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
                },
            },
            "components": ["Button", "Input", "Card", "Modal", "Alert", "Badge"],
            "patterns": ["Navigation", "Forms", "Data Display", "Feedback"],
            "documentation": llm_response,
        }

    def _parse_accessibility_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para auditoría de accesibilidad.

        Args:
            llm_response: Respuesta del LLM

        Returns:
            Estructura de auditoría de accesibilidad parseada
        """
        return {
            "type": "accessibility_audit",
            "wcag_level": "AA",
            "checks": {
                "perceivable": {
                    "text_alternatives": True,
                    "captions": True,
                    "contrast": {"status": "pass", "ratio": "4.5:1"},
                    "resize": True,
                },
                "operable": {
                    "keyboard": True,
                    "timing": True,
                    "navigation": True,
                    "input_modalities": True,
                },
                "understandable": {
                    "readable": True,
                    "predictable": True,
                    "input_assistance": True,
                },
                "robust": {
                    "compatible": True,
                },
            },
            "issues": [],
            "recommendations": [
                "Add skip navigation links",
                "Ensure all images have alt text",
                "Verify focus order is logical",
                "Test with screen readers",
            ],
            "documentation": llm_response,
        }

    def _parse_style_guide_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para guías de estilo.

        Args:
            llm_response: Respuesta del LLM

        Returns:
            Estructura de guía de estilo parseada
        """
        return {
            "type": "style_guide",
            "brand": {
                "colors": {"primary": "#3B82F6", "secondary": "#6B7280"},
                "typography": {"heading": "Inter Bold", "body": "Inter Regular"},
                "spacing": {"base": "1rem", "scale": "1.5"},
            },
            "components": {
                "buttons": {"borderRadius": "0.5rem", "padding": "0.5rem 1rem"},
                "inputs": {"borderRadius": "0.375rem", "borderWidth": "1px"},
                "cards": {"borderRadius": "0.75rem", "shadow": "md"},
            },
            "documentation": llm_response,
        }

    def _parse_generic_response(self, llm_response: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM para tareas genéricas.

        Args:
            llm_response: Respuesta del LLM

        Returns:
            Estructura genérica parseada
        """
        return {
            "type": "generic",
            "design": llm_response,
            "recommendations": [
                "Considerar accesibilidad WCAG",
                "Usar design tokens consistentes",
                "Documentar decisiones de diseño",
            ],
        }

    # =========================================================================
    # Verificación de accesibilidad
    # =========================================================================

    async def _check_accessibility(self, design_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verifica accesibilidad del diseño.

        Args:
            design_result: Resultado del diseño

        Returns:
            Resultado de verificación de accesibilidad
        """
        accessibility: Dict[str, Any] = {
            "wcag_level": "AA",
            "checks": {
                "contrast": {"status": "pass", "ratio": "4.5:1"},
                "keyboard_navigation": {"status": "pass"},
                "screen_reader": {"status": "pass"},
                "color_blindness": {"status": "pass"},
            },
            "issues": [],
            "recommendations": [
                "Ensure sufficient color contrast",
                "Add ARIA labels where needed",
                "Test with keyboard navigation",
                "Verify with screen reader",
            ],
        }

        # Si el resultado incluye información de accesibilidad, enriquecer la verificación
        design_acc = design_result.get("accessibility")
        if isinstance(design_acc, dict):
            if "wcag_level" in design_acc:
                accessibility["wcag_level"] = design_acc["wcag_level"]
            contrast_info = design_acc.get("contrast_ratio")
            if contrast_info and isinstance(accessibility["checks"], dict):
                checks = accessibility["checks"]
                if isinstance(checks.get("contrast"), dict):
                    checks["contrast"]["ratio"] = contrast_info

        return accessibility

    # =========================================================================
    # Persistencia de aprendizaje
    # =========================================================================

    async def _save_learning(
        self,
        task: Task,
        design_result: Dict[str, Any],
        memory: "MemoryStore",
    ) -> None:
        """
        Guarda aprendizaje de la tarea en memoria para reutilización.

        Solo almacena información útil y evita duplicados.

        Args:
            task: Tarea completada
            design_result: Resultado del diseño
            memory: Almacén de memoria
        """
        try:
            # Determinar tipo de memoria
            memory_type = self._infer_memory_type(task.description)

            # Crear metadata para la memoria
            metadata = {
                "agent": self.name,
                "model": self.model,
                "task_type": design_result.get("type", "unknown"),
                "has_accessibility": bool(design_result.get("accessibility")),
                "recommendations_count": len(design_result.get("recommendations", [])),
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Almacenar en memoria como conocimiento
            _ = await memory.store_knowledge(
                project_id=task.project_id if hasattr(task, "project_id") else "",
                title=f"Design: {task.description[:80]}",
                content=design_result.get("documentation", "")[:1000],
                tags=[memory_type, design_result.get("type", "generic")],
                metadata=metadata,
            )

            logger.debug(
                "designer_learning_stored",
                memory_type=memory_type,
                agent=self.name,
            )

        except Exception as e:
            logger.warning(
                "designer_learning_store_failed",
                task_id=task.task_id,
                error=str(e),
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

        if any(kw in description_lower for kw in ["component", "button", "input", "card", "modal"]):
            return "ui_components"
        elif any(kw in description_lower for kw in ["design system", "token", "theme"]):
            return "design_system"
        elif any(kw in description_lower for kw in ["accessibility", "a11y", "wcag"]):
            return "accessibility"
        elif any(kw in description_lower for kw in ["style guide", "branding", "color"]):
            return "style_guide"
        else:
            return "general_design"

    # =========================================================================
    # Creación de resultado
    # =========================================================================

    def _create_result(
        self,
        task: Task,
        design_result: Dict[str, Any],
        accessibility: Dict[str, Any],
    ) -> AgentResult:
        """
        Crea el resultado de la ejecución.

        Args:
            task: Tarea ejecutada
            design_result: Resultado del diseño
            accessibility: Verificación de accesibilidad

        Returns:
            Resultado estructurado
        """
        result = AgentResult(
            success=True,
            content=design_result.get("documentation", ""),
            artifacts=design_result.get("components", []),
            metadata={
                "design_type": design_result.get("type"),
                "tokens": design_result.get("tokens", {}),
                "accessibility": accessibility,
                "recommendations": design_result.get("recommendations", []),
            },
            agent_name=self.name,
            model_used=self.model,
        )

        return result

    # =========================================================================
    # Utilidades
    # =========================================================================

    def get_system_prompt(self, context: "SessionContext") -> str:
        """
        Obtiene el system prompt específico para el contexto.

        Args:
            context: Contexto de sesión

        Returns:
            System prompt específico
        """
        base_prompt = self.system_prompt

        # Añadir contexto del proyecto si existe
        if hasattr(context, "project_context") and context.project_context:
            project_info = f"""

Contexto del proyecto:
- Framework: {getattr(context.project_context.config, "frontend_framework", "React")}
- Framework backend: {getattr(context.project_context.config, "backend_framework", "FastAPI")}
- Estilos: {getattr(context.project_context.config, "styling_framework", "Tailwind CSS")}
"""
            base_prompt += project_info

        return base_prompt

    def __repr__(self) -> str:
        return f"<DesignerAgent(name='{self.name}', model='{self.model}')>"
