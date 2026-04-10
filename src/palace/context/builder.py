"""Módulo Constructor de Contexto - Palace Framework

Este módulo implementa el ContextBuilder, el componente central del módulo de
contexto que combina múltiples fuentes de contexto (proyecto, memoria, sesión,
tarea) en un prompt estructurado y optimizado para el agente que lo recibirá.

El ContextBuilder gestiona:
    - Presupuesto de tokens por sección
    - Selección inteligente de contexto basada en relevancia
    - Truncamiento respetando los límites de cada sección
    - Ensamblaje ordenado del prompt final

Flujo principal (alineado con canonico.md):
    1. Recibir tarea → Calcular presupuestos de tokens
    2. Consultar memoria → Recuperar contexto relevante (RAG)
    3. Cargar contexto → Construir secciones de proyecto y sesión
    4. Ejecutar agentes → Proveer prompt estructurado
    5. Validar → Verificar que el prompt no excede el presupuesto
    6. Almacenar aprendizaje → (Manejado externamente por MemoryStore)
"""

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.context.loader import ProjectLoader
from palace.context.retriever import ContextRetriever, RetrievalConfig
from palace.context.session import SessionManager
from palace.context.types import (
    ContextEntry,
    ContextType,
    ProjectConfig,
    RetrievedContext,
    SessionConfig,
)
from palace.core.types import MemoryType

if TYPE_CHECKING:
    from palace.memory.base import MemoryStore

logger = structlog.get_logger(__name__)


class ContextBuilder:
    """Context builder for agents.

    Combines multiple context sources (project, memory, session, task)
    into a structured prompt optimized for the receiving agent.
    Manages token budgets and intelligent context selection.
    """

    # Token budget allocation (percentages of max_context_tokens)
    SYSTEM_PROMPT_BUDGET_PCT = 0.10  # 10% for system prompt
    PROJECT_CONTEXT_BUDGET_PCT = 0.30  # 30% for project context
    MEMORY_CONTEXT_BUDGET_PCT = 0.30  # 30% for memory/RAG context
    SESSION_CONTEXT_BUDGET_PCT = 0.20  # 20% for session history
    TASK_CONTEXT_BUDGET_PCT = 0.10  # 10% for current task

    def __init__(
        self,
        memory_store: "MemoryStore",
        max_context_tokens: int = 8000,
        retriever_config: Optional[RetrievalConfig] = None,
        session_config: Optional[SessionConfig] = None,
    ) -> None:
        """Initialize the ContextBuilder.

        Args:
            memory_store: The memory store for context retrieval and session management.
            max_context_tokens: Maximum total tokens for the assembled prompt.
            retriever_config: Optional configuration for the context retriever.
            session_config: Optional configuration for the session manager.
        """
        self._memory_store = memory_store
        self._max_context_tokens = max_context_tokens
        self._retriever = ContextRetriever(memory_store, retriever_config or RetrievalConfig())
        self._session_manager = SessionManager(memory_store, session_config or SessionConfig())
        self._project_loader: Optional[ProjectLoader] = None
        self._loaded_projects: Dict[str, ProjectConfig] = {}

        logger.info(
            "context_builder_initialized",
            max_context_tokens=max_context_tokens,
            system_budget_pct=self.SYSTEM_PROMPT_BUDGET_PCT,
            project_budget_pct=self.PROJECT_CONTEXT_BUDGET_PCT,
            memory_budget_pct=self.MEMORY_CONTEXT_BUDGET_PCT,
            session_budget_pct=self.SESSION_CONTEXT_BUDGET_PCT,
            task_budget_pct=self.TASK_CONTEXT_BUDGET_PCT,
        )

    # -------------------------------------------------------------------------
    # Public Async Methods
    # -------------------------------------------------------------------------

    async def build_context(
        self,
        project_id: str,
        query: str,
        agent_role: str,
        task_description: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """Build the complete context prompt for an agent.

        This is the main entry point for context construction. It follows
        a 6-step process aligned with the framework's canonical flow:

        1. **Receive task** → Calculate token budgets for each section.
        2. **Consult memory** → Retrieve relevant context via RAG from
           the memory store (semantic, episodic, procedural).
        3. **Load context** → Build project and session sections with
           loaded files and conversation history.
        4. **Execute agents** → Assemble the structured prompt that the
           agent will consume as its working context.
        5. **Validate** → Ensure each section respects its token budget
           via truncation; never exceed the total limit.
        6. **Store learning** → (Handled externally by MemoryStore after
           the agent produces output.)

        Args:
            project_id: Identifier of the project to load context for.
            query: The query or task description to retrieve relevant
                memory context for.
            agent_role: The role of the agent that will receive this
                context (used to tailor retrieval and system prompt).
            task_description: Optional description of the current task
                to include in the prompt.
            session_id: Optional session ID to include conversation
                history from.

        Returns:
            A fully assembled prompt string containing all context
            sections, ready to be passed to an agent.
        """
        logger.info(
            "building_context",
            project_id=project_id,
            agent_role=agent_role,
            has_task=bool(task_description),
            has_session=bool(session_id),
        )

        # Step 1: Calculate token budgets for each section
        budgets = self._calculate_budgets()
        logger.debug("token_budgets_calculated", **budgets)

        # Step 2: Build system prompt section (agent-specific instructions)
        try:
            system_section = self._build_system_section(agent_role)
        except Exception as exc:
            logger.error("system_section_build_failed", error=str(exc))
            system_section = "## Agent Role\n\n[Error: could not build system section]"

        # Step 3: Build project context section (loaded files)
        try:
            project_section = await self.build_project_section(project_id, budgets["project"])
        except Exception as exc:
            logger.error(
                "project_section_build_failed",
                project_id=project_id,
                error=str(exc),
            )
            project_section = "## Project Context\n\n[Error: could not load project context]"

        # Step 4: Build memory context section (RAG retrieval)
        try:
            memory_section = await self.build_memory_section(
                project_id, query, agent_role, budgets["memory"]
            )
        except Exception as exc:
            logger.error(
                "memory_section_build_failed",
                project_id=project_id,
                error=str(exc),
            )
            memory_section = (
                "## Relevant Context from Memory\n\n[Error: could not retrieve memory context]"
            )

        # Step 5: Build session context section (conversation history)
        try:
            session_section = await self.build_session_section(
                project_id, session_id, budgets["session"]
            )
        except Exception as exc:
            logger.error(
                "session_section_build_failed",
                project_id=project_id,
                error=str(exc),
            )
            session_section = "## Conversation History\n\n[Error: could not load session history]"

        # Step 6: Build task context section (current task)
        if task_description:
            try:
                task_section = await self.build_task_section(task_description, budgets["task"])
            except Exception as exc:
                logger.error("task_section_build_failed", error=str(exc))
                task_section = "## Current Task\n\n[Error: could not build task section]"
        else:
            task_section = ""

        # Assemble all sections into final prompt
        sections = {
            "system": system_section,
            "project": project_section,
            "memory": memory_section,
            "session": session_section,
            "task": task_section,
        }
        prompt = self._assemble_prompt(sections)

        total_tokens = self._estimate_tokens(prompt)
        logger.info(
            "context_built",
            project_id=project_id,
            agent_role=agent_role,
            estimated_tokens=total_tokens,
            max_tokens=self._max_context_tokens,
            sections_included=[k for k, v in sections.items() if v],
        )

        return prompt

    async def build_project_section(
        self,
        project_id: str,
        token_budget: int,
    ) -> str:
        """Build the project context section.

        Loads the project configuration and formats key sections
        (architecture, stack, conventions, decisions, constraints),
        truncating each to fit within the token budget.

        Args:
            project_id: The project identifier to load context for.
            token_budget: Maximum tokens allowed for this section.

        Returns:
            A formatted string with the project context section,
            or an empty string with a note if no project is loaded.
        """
        try:
            project = await self._load_or_get_project(project_id)
        except Exception as exc:
            logger.error(
                "project_load_failed_in_section",
                project_id=project_id,
                error=str(exc),
            )
            project = None

        if project is None:
            note = "No project context loaded. Use load_project() first."
            logger.debug("no_project_context", project_id=project_id)
            return f"## Project Context\n\n{note}"

        # Format technology stack
        stack_lines: List[str] = []
        for category, technology in project.stack.items():
            stack_lines.append(f"- **{category}**: {technology}")
        stack_text = "\n".join(stack_lines) if stack_lines else "No stack information available."

        # Format conventions
        conventions_text = (
            "\n".join(f"- {c}" for c in project.conventions)
            if project.conventions
            else "No conventions defined."
        )

        # Format decisions
        decisions_text = (
            "\n".join(f"- {d}" for d in project.decisions)
            if project.decisions
            else "No decisions recorded."
        )

        # Format constraints
        constraints_text = (
            "\n".join(f"- {c}" for c in project.constraints)
            if project.constraints
            else "No constraints defined."
        )

        # Get architecture content from description
        architecture_text = project.description or "No architecture overview available."

        # Build the full section
        section = (
            f"## Project Context\n\n"
            f"### Technology Stack\n{stack_text}\n\n"
            f"### Architecture\n{architecture_text}\n\n"
            f"### Conventions\n{conventions_text}\n\n"
            f"### Key Decisions\n{decisions_text}\n\n"
            f"### Constraints\n{constraints_text}"
        )

        return self._truncate_to_tokens(section, token_budget)

    async def build_memory_section(
        self,
        project_id: str,
        query: str,
        agent_role: str,
        token_budget: int,
    ) -> str:
        """Build the memory context section using RAG retrieval.

        Retrieves relevant context from the memory store tailored
        to the agent's role, and formats each entry with source
        attribution and relevance scores.

        Args:
            project_id: The project ID to scope the retrieval.
            query: The search query for relevant context.
            agent_role: The role of the requesting agent.
            token_budget: Maximum tokens allowed for this section.

        Returns:
            A formatted string with retrieved memory entries,
            truncated to the token budget.
        """
        try:
            retrieved: RetrievedContext = await self._retriever.retrieve_for_agent(
                project_id=project_id,
                query=query,
                agent_role=agent_role,
            )
        except Exception as exc:
            logger.error(
                "memory_retrieval_failed",
                project_id=project_id,
                query=query,
                error=str(exc),
            )
            return ""

        if not retrieved.entries:
            logger.debug(
                "no_memory_entries_retrieved",
                project_id=project_id,
                query=query,
            )
            return ""

        # Format each retrieved entry
        parts: List[str] = ["## Relevant Context from Memory\n"]
        for entry in retrieved.entries:
            entry_text = (
                f"[Source: {entry.source}] (relevance: {entry.relevance_score:.2f})\n"
                f"{entry.content}\n\n---"
            )
            parts.append(entry_text)

        full_section = "\n\n".join(parts)

        logger.debug(
            "memory_section_built",
            project_id=project_id,
            entries_count=len(retrieved.entries),
            total_tokens=retrieved.total_tokens,
            truncated=retrieved.truncated,
        )

        return self._truncate_to_tokens(full_section, token_budget)

    async def build_session_section(
        self,
        project_id: str,
        session_id: Optional[str],
        token_budget: int,
    ) -> str:
        """Build the session/conversation history section.

        If a session_id is provided, retrieves recent conversation
        history from the session manager and formats it as a
        conversation transcript.

        Args:
            project_id: The project ID for logging purposes.
            session_id: The session ID to retrieve history from.
                If None, no session section is built.
            token_budget: Maximum tokens allowed for this section.

        Returns:
            A formatted string with conversation history,
            or an empty string if no session_id is provided.
        """
        if session_id is None:
            logger.debug("no_session_id_provided", project_id=project_id)
            return ""

        try:
            recent_context = await self._session_manager.get_recent_context(
                session_id=session_id,
            )
        except Exception as exc:
            logger.warning(
                "session_context_retrieval_failed",
                session_id=session_id,
                error=str(exc),
            )
            return ""

        if not recent_context or not recent_context.strip():
            logger.debug("empty_session_context", session_id=session_id)
            return ""

        section = f"## Conversation History\n\n{recent_context}"

        return self._truncate_to_tokens(section, token_budget)

    async def build_task_section(
        self,
        task_description: str,
        token_budget: int,
    ) -> str:
        """Build the current task section.

        Formats the task description, truncating if needed
        to fit within the token budget.

        Args:
            task_description: The description of the current task.
            token_budget: Maximum tokens allowed for this section.

        Returns:
            A formatted string with the task description.
        """
        section = f"## Current Task\n\n{task_description}"

        return self._truncate_to_tokens(section, token_budget)

    async def load_project(self, project_path: str) -> ProjectConfig:
        """Load a project from the given path.

        Creates a ProjectLoader instance, loads the project context,
        and stores the resulting configuration for later retrieval.

        Args:
            project_path: The root path of the project to load.

        Returns:
            The loaded ProjectConfig.

        Raises:
            OSError: If the project path cannot be accessed.
        """
        path = Path(project_path)
        loader = ProjectLoader(path)
        config = await loader.load()

        self._loaded_projects[config.project_id] = config
        self._project_loader = loader

        logger.info(
            "project_loaded_into_builder",
            project_id=config.project_id,
            project_name=config.name,
            path=project_path,
        )

        return config

    # -------------------------------------------------------------------------
    # Private Methods
    # -------------------------------------------------------------------------

    def _calculate_budgets(self) -> Dict[str, int]:
        """Calculate token budgets for each section based on max_context_tokens.

        Uses the percentage constants to allocate tokens to each section.
        Budgets are rounded down to ensure we never exceed the total.

        Returns:
            A dictionary with keys "system", "project", "memory",
            "session", "task" and their respective token budgets.
        """
        max_tokens = self._max_context_tokens
        return {
            "system": int(max_tokens * self.SYSTEM_PROMPT_BUDGET_PCT),
            "project": int(max_tokens * self.PROJECT_CONTEXT_BUDGET_PCT),
            "memory": int(max_tokens * self.MEMORY_CONTEXT_BUDGET_PCT),
            "session": int(max_tokens * self.SESSION_CONTEXT_BUDGET_PCT),
            "task": int(max_tokens * self.TASK_CONTEXT_BUDGET_PCT),
        }

    def _assemble_prompt(self, sections: Dict[str, str]) -> str:
        """Assemble all sections into a single prompt string.

        Sections are ordered: system, project, memory, session, task.
        Empty sections are skipped. Separators are added between
        sections for readability.

        Args:
            sections: Dictionary mapping section names to their
                formatted content strings.

        Returns:
            The assembled prompt string with all non-empty sections.
        """
        order = ["system", "project", "memory", "session", "task"]
        parts: List[str] = []

        for section_name in order:
            content = sections.get(section_name, "")
            if content and content.strip():
                parts.append(content.strip())

        return "\n\n---\n\n".join(parts)

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within a token budget.

        Estimates the token count of the text and, if it exceeds the
        budget, truncates by words and appends "..." to indicate
        truncation.

        Args:
            text: The text to potentially truncate.
            max_tokens: The maximum number of tokens allowed.

        Returns:
            The original text if within budget, or a truncated
            version with "..." appended.
        """
        estimated = self._estimate_tokens(text)
        if estimated <= max_tokens:
            return text

        # Estimate words per token (inverse of 1.3 tokens per word)
        # max_tokens ≈ words * 1.3 → words ≈ max_tokens / 1.3
        target_words = int(max_tokens / 1.3)
        words = text.split()

        if target_words <= 0:
            return "..."

        truncated = " ".join(words[:target_words]) + "..."
        logger.debug(
            "text_truncated",
            original_tokens=estimated,
            max_tokens=max_tokens,
            target_words=target_words,
        )

        return truncated

    def _estimate_tokens(self, text: str) -> int:
        """Estimate the number of tokens in a text string.

        Uses a simple heuristic: each word is approximately 1.3 tokens.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated number of tokens.
        """
        return int(len(text.split()) * 1.3)

    def _build_system_section(self, agent_role: str) -> str:
        """Build a minimal system prompt section.

        Includes the agent role and basic instructions for using
        the provided context.

        Args:
            agent_role: The role of the agent that will receive
                this context.

        Returns:
            A formatted system prompt section string.
        """
        return (
            f"## Agent Role\n\n"
            f"You are the **{agent_role}** agent. "
            f"Use the following context to complete your task."
        )

    async def _load_or_get_project(
        self,
        project_id: str,
    ) -> Optional[ProjectConfig]:
        """Load or retrieve a cached project configuration.

        First checks the local cache of loaded projects. If not found,
        attempts to retrieve project-level context from the memory store
        via the retriever. If memory results are found, constructs a
        basic ProjectConfig from them.

        Args:
            project_id: The project identifier to look up.

        Returns:
            The ProjectConfig if found, or None if unavailable.
        """
        # Check cache first
        if project_id in self._loaded_projects:
            logger.debug("project_found_in_cache", project_id=project_id)
            return self._loaded_projects[project_id]

        # Try to retrieve from memory
        try:
            retrieved = await self._retriever.retrieve(
                project_id=project_id,
                query=f"project configuration for {project_id}",
                context_type=ContextType.CONFIG,
            )

            if retrieved.entries:
                # Attempt to construct a minimal ProjectConfig from
                # retrieved entries
                stack: Dict[str, str] = {}
                conventions: List[str] = []
                decisions: List[str] = []
                constraints: List[str] = []
                description: Optional[str] = None

                for entry in retrieved.entries:
                    if entry.context_type == ContextType.STACK:
                        stack[entry.title] = entry.content
                    elif entry.context_type == ContextType.CONVENTIONS:
                        conventions.append(entry.title)
                    elif entry.context_type == ContextType.DECISIONS:
                        decisions.append(entry.title)
                    elif entry.context_type == ContextType.CONSTRAINTS:
                        constraints.append(entry.title)
                    elif entry.context_type == ContextType.ARCHITECTURE:
                        description = entry.title

                if stack or conventions or decisions or constraints:
                    config = ProjectConfig(
                        project_id=project_id,
                        name=project_id,
                        description=description,
                        root_path=Path("."),
                        context_path=Path(".") / "ai_context",
                        stack=stack,
                        conventions=conventions,
                        decisions=decisions,
                        constraints=constraints,
                        last_loaded=datetime.utcnow(),
                    )
                    self._loaded_projects[project_id] = config

                    logger.info(
                        "project_loaded_from_memory",
                        project_id=project_id,
                        entries_used=len(retrieved.entries),
                    )
                    return config

        except Exception as exc:
            logger.warning(
                "project_memory_lookup_failed",
                project_id=project_id,
                error=str(exc),
            )

        logger.debug("project_not_found", project_id=project_id)
        return None
