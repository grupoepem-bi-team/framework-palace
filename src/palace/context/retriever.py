"""
Módulo de Recuperación de Contexto - Palace Framework

Este módulo implementa la recuperación de contexto relevante desde el
almacén de memoria utilizando búsqueda semántica (RAG - Retrieval
Augmented Generation). Proporciona capacidades de búsqueda vectorial
para enriquecer el contexto de los agentes durante la ejecución de tareas.

Componentes:
    - RetrievalConfig: Configuración para la recuperación de contexto
    - ContextRetriever: Recuperador de contexto basado en RAG
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog

from palace.context.types import ContextEntry, ContextType, RetrievedContext
from palace.core.types import MemoryType

if TYPE_CHECKING:
    from palace.memory.base import MemoryStore

logger = structlog.get_logger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for context retrieval."""

    top_k: int = 5
    """Maximum number of results per memory type."""

    min_relevance_score: float = 0.3
    """Minimum relevance score to include a result."""

    max_total_tokens: int = 4000
    """Maximum total tokens for retrieved context."""

    memory_types: List[MemoryType] = field(
        default_factory=lambda: [
            MemoryType.SEMANTIC,
            MemoryType.EPISODIC,
            MemoryType.PROCEDURAL,
        ]
    )
    """Memory types to search."""

    include_project_context: bool = True
    """Whether to include project-level context."""

    deduplicate: bool = True
    """Whether to remove duplicate entries."""

    boost_recent: bool = True
    """Whether to boost recently accessed entries."""

    recent_boost_factor: float = 1.2
    """Factor to boost recent entries by."""


class ContextRetriever:
    """Recuperador de contexto basado en RAG.

    Utiliza búsqueda semántica en la memoria vectorial para encontrar
    contexto relevante para una consulta dada.
    """

    def __init__(
        self,
        memory_store: "MemoryStore",
        config: Optional[RetrievalConfig] = None,
    ):
        """
        Initialize the context retriever.

        Args:
            memory_store: The memory store to search for context.
            config: Optional retrieval configuration. Defaults to RetrievalConfig().
        """
        self._memory_store = memory_store
        self._config = config or RetrievalConfig()

    async def retrieve(
        self,
        project_id: str,
        query: str,
        context_type: Optional[ContextType] = None,
    ) -> RetrievedContext:
        """
        Main retrieval method.

        Searches memory for each configured memory type, filters and ranks
        results by relevance, and returns a RetrievedContext with all metadata.

        Args:
            project_id: The project ID to scope the search.
            query: The search query string.
            context_type: Optional context type to filter results.

        Returns:
            A RetrievedContext containing matching entries and metadata.
        """
        start_time = datetime.utcnow()
        all_entries: List[ContextEntry] = []

        for mem_type in self._config.memory_types:
            try:
                results = await self._memory_store.search(
                    project_id=project_id,
                    query=query,
                    memory_type=mem_type,
                    top_k=self._config.top_k,
                )
                entries = self._convert_to_entries(results)
                all_entries.extend(entries)
            except Exception as e:
                logger.error(
                    "memory_search_failed",
                    memory_type=mem_type.value if hasattr(mem_type, "value") else str(mem_type),
                    project_id=project_id,
                    error=str(e),
                )
                continue

        # Include project-level context if configured
        if self._config.include_project_context:
            try:
                project_results = await self._memory_store.search(
                    project_id=project_id,
                    query=query,
                    memory_type=MemoryType.PROJECT,
                    top_k=self._config.top_k,
                )
                project_entries = self._convert_to_entries(project_results)
                all_entries.extend(project_entries)
            except Exception as e:
                logger.error(
                    "project_context_search_failed",
                    project_id=project_id,
                    error=str(e),
                )

        # Filter by context type if specified
        if context_type is not None:
            all_entries = [entry for entry in all_entries if entry.context_type == context_type]

        # Apply relevance filtering
        all_entries = self._apply_relevance_filter(all_entries)

        # Apply recency boosting
        all_entries = self._apply_recency_boost(all_entries)

        # Deduplicate entries
        all_entries = self._deduplicate_entries(all_entries)

        # Sort by relevance score (descending)
        all_entries.sort(key=lambda e: e.relevance_score, reverse=True)

        # Truncate to token limit
        truncated = False
        all_entries, truncated = self._truncate_to_token_limit(all_entries)

        # Calculate total tokens
        total_tokens = sum(entry.token_count for entry in all_entries)

        # Collect sources
        sources = list({entry.source for entry in all_entries if entry.source})

        end_time = datetime.utcnow()
        retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)

        return RetrievedContext(
            query=query,
            entries=all_entries,
            total_tokens=total_tokens,
            truncated=truncated,
            sources=sources,
            memory_hits=len(all_entries),
            retrieval_time_ms=retrieval_time_ms,
        )

    async def retrieve_for_agent(
        self,
        project_id: str,
        query: str,
        agent_role: str,
    ) -> RetrievedContext:
        """
        Retrieve context tailored for a specific agent.

        Adjusts memory types based on the agent's role to prioritize
        the most relevant types of context for that agent's work.

        Args:
            project_id: The project ID to scope the search.
            query: The search query string.
            agent_role: The role of the agent requesting context.

        Returns:
            A RetrievedContext with agent-optimized results.
        """
        agent_memory_types = self._get_agent_memory_types(agent_role)

        # Create agent-specific config
        agent_config = RetrievalConfig(
            top_k=self._config.top_k,
            min_relevance_score=self._config.min_relevance_score,
            max_total_tokens=self._config.max_total_tokens,
            memory_types=agent_memory_types,
            include_project_context=self._config.include_project_context,
            deduplicate=self._config.deduplicate,
            boost_recent=self._config.boost_recent,
            recent_boost_factor=self._config.recent_boost_factor,
        )

        # Temporarily swap config
        original_config = self._config
        self._config = agent_config

        try:
            result = await self.retrieve(
                project_id=project_id,
                query=query,
            )
        finally:
            # Restore original config
            self._config = original_config

        return result

    async def retrieve_project_context(
        self,
        project_id: str,
    ) -> List[ContextEntry]:
        """
        Retrieve all project-level context from memory.

        Searches memory for entries of MemoryType.PROJECT and returns
        them as ContextEntry objects sorted by relevance.

        Args:
            project_id: The project ID to scope the search.

        Returns:
            List of ContextEntry objects sorted by relevance score.
        """
        try:
            results = await self._memory_store.search(
                project_id=project_id,
                query="*",
                memory_type=MemoryType.PROJECT,
                top_k=self._config.top_k,
            )
            entries = self._convert_to_entries(results)
        except Exception as e:
            logger.error(
                "project_context_retrieval_failed",
                project_id=project_id,
                error=str(e),
            )
            return []

        # Sort by relevance score (descending)
        entries.sort(key=lambda e: e.relevance_score, reverse=True)
        return entries

    def _convert_to_entries(
        self,
        results: List[Dict[str, Any]],
        context_type: ContextType = ContextType.MEMORY,
    ) -> List[ContextEntry]:
        """
        Convert memory search results to ContextEntry objects.

        Each result dict may have keys: "content", "score", "metadata", "entry_id".
        The score is mapped to relevance_score, and metadata is used to
        determine source and title.

        Args:
            results: List of result dictionaries from memory search.
            context_type: The context type to assign to entries.

        Returns:
            List of ContextEntry objects.
        """
        entries: List[ContextEntry] = []

        for result in results:
            try:
                content = result.get("content", "")
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})
                entry_id = result.get("entry_id", None)

                source = metadata.get("source", result.get("source", "memory"))
                title = metadata.get("title", content[:80] if content else "Untitled")

                # Determine context type from metadata if available
                entry_context_type = context_type
                if "context_type" in metadata:
                    try:
                        entry_context_type = ContextType(metadata["context_type"])
                    except (ValueError, KeyError):
                        pass

                # Estimate token count
                token_count = self._estimate_tokens(content) if content else 0

                # Build metadata without duplicating keys already in ContextEntry
                entry_metadata = {
                    k: v
                    for k, v in metadata.items()
                    if k not in ("source", "title", "context_type")
                }
                if entry_id:
                    entry_metadata["memory_entry_id"] = str(entry_id)

                # Determine created_at from metadata if available
                created_at = datetime.utcnow()
                if "created_at" in metadata:
                    if isinstance(metadata["created_at"], datetime):
                        created_at = metadata["created_at"]
                    elif isinstance(metadata["created_at"], str):
                        try:
                            created_at = datetime.fromisoformat(metadata["created_at"])
                        except (ValueError, TypeError):
                            pass

                entry = ContextEntry(
                    context_type=entry_context_type,
                    source=source,
                    title=title,
                    content=content,
                    metadata=entry_metadata,
                    relevance_score=min(max(score, 0.0), 1.0),
                    token_count=token_count,
                    created_at=created_at,
                )
                entries.append(entry)
            except Exception as e:
                logger.warning(
                    "failed_to_convert_result",
                    error=str(e),
                    result_keys=list(result.keys()) if isinstance(result, dict) else None,
                )
                continue

        return entries

    def _apply_relevance_filter(
        self,
        entries: List[ContextEntry],
    ) -> List[ContextEntry]:
        """
        Filter out entries below the minimum relevance score.

        Args:
            entries: List of context entries to filter.

        Returns:
            Filtered list of entries meeting the minimum relevance threshold.
        """
        return [
            entry for entry in entries if entry.relevance_score >= self._config.min_relevance_score
        ]

    def _apply_recency_boost(
        self,
        entries: List[ContextEntry],
    ) -> List[ContextEntry]:
        """
        Boost relevance scores of recently created entries.

        Entries created within the last 24 hours receive the full boost
        factor. Entries created within the last 7 days receive half the
        boost. Relevance scores are capped at 1.0.

        Args:
            entries: List of context entries to boost.

        Returns:
            List of entries with adjusted relevance scores.
        """
        if not self._config.boost_recent:
            return entries

        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        half_boost = 1.0 + (self._config.recent_boost_factor - 1.0) / 2

        boosted: List[ContextEntry] = []

        for entry in entries:
            created_at = entry.created_at

            # Skip if created_at is not a proper datetime
            if not isinstance(created_at, datetime):
                boosted.append(entry)
                continue

            if created_at >= last_24h:
                # Full boost for entries within last 24 hours
                new_score = entry.relevance_score * self._config.recent_boost_factor
            elif created_at >= last_7d:
                # Half boost for entries within last 7 days
                new_score = entry.relevance_score * half_boost
            else:
                boosted.append(entry)
                continue

            # Cap at 1.0
            new_score = min(new_score, 1.0)

            boosted_entry = entry.model_copy(update={"relevance_score": new_score})
            boosted.append(boosted_entry)

        return boosted

    def _deduplicate_entries(
        self,
        entries: List[ContextEntry],
    ) -> List[ContextEntry]:
        """
        Remove entries with duplicate content.

        Deduplication is based on the first 200 characters of content.
        When duplicates are found, the entry with the higher relevance
        score is kept.

        Args:
            entries: List of context entries to deduplicate.

        Returns:
            Deduplicated list of entries.
        """
        if not self._config.deduplicate:
            return entries

        seen: Dict[str, ContextEntry] = {}

        for entry in entries:
            content_key = entry.content[:200] if entry.content else ""

            if content_key in seen:
                # Keep the one with higher relevance score
                if entry.relevance_score > seen[content_key].relevance_score:
                    seen[content_key] = entry
            else:
                seen[content_key] = entry

        return list(seen.values())

    def _truncate_to_token_limit(
        self,
        entries: List[ContextEntry],
    ) -> tuple[List[ContextEntry], bool]:
        """
        Truncate entries to fit within the total token limit.

        Entries are removed from the end (lowest relevance) until the
        total token count is within the configured limit.

        Args:
            entries: List of context entries sorted by relevance (descending).

        Returns:
            A tuple of (truncated entries list, whether truncation occurred).
        """
        total_tokens = sum(entry.token_count for entry in entries)

        if total_tokens <= self._config.max_total_tokens:
            return entries, False

        truncated_entries: List[ContextEntry] = []
        current_tokens = 0

        for entry in entries:
            if current_tokens + entry.token_count <= self._config.max_total_tokens:
                truncated_entries.append(entry)
                current_tokens += entry.token_count
            else:
                # This entry would exceed the limit; skip it and all remaining
                break

        return truncated_entries, True

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.

        Uses a simple heuristic: word count multiplied by 1.3 to
        approximate subword tokenization overhead.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return int(len(text.split()) * 1.3)

    def _get_agent_memory_types(self, agent_role: str) -> List[MemoryType]:
        """
        Return the appropriate memory types for each agent role.

        Different agent roles benefit from different types of context.
        This method maps roles to their prioritized memory types.

        Args:
            agent_role: The role of the agent.

        Returns:
            List of MemoryType values appropriate for the agent role.
        """
        role_mapping: Dict[str, List[MemoryType]] = {
            "backend": [MemoryType.SEMANTIC, MemoryType.PROCEDURAL],
            "frontend": [MemoryType.SEMANTIC, MemoryType.EPISODIC],
            "dba": [MemoryType.SEMANTIC],
            "devops": [MemoryType.PROCEDURAL],
            "infra": [MemoryType.SEMANTIC],
            "qa": [MemoryType.EPISODIC, MemoryType.PROCEDURAL],
            "designer": [MemoryType.SEMANTIC],
            "reviewer": [MemoryType.SEMANTIC, MemoryType.EPISODIC],
            "orchestrator": [
                MemoryType.SEMANTIC,
                MemoryType.EPISODIC,
                MemoryType.PROCEDURAL,
            ],
        }

        return role_mapping.get(
            agent_role.lower(),
            [MemoryType.SEMANTIC, MemoryType.EPISODIC, MemoryType.PROCEDURAL],
        )
