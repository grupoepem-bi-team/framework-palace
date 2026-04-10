"""Gestión de calidad de memoria para el Palace Framework.

Este módulo implementa la gestión de calidad de las entradas de memoria,
incluyendo deduplicación, expiración, scoring de relevancia y limpieza
periódica para mantener la memoria libre de datos irrelevantes o duplicados.

Parte del Módulo 11 - Refinement.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import structlog


class QualityScore(str, Enum):
    """Quality score classification for memory entries."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    IRRELEVANT = "irrelevant"


@dataclass
class CleanupPolicy:
    """Policy configuration for memory cleanup operations."""

    max_entries_per_project: int = 10000
    min_relevance_score: float = 0.3
    expire_after_days: int = 90
    expire_episodic_after_days: int = 30
    deduplication_similarity_threshold: float = 0.85
    cleanup_interval_hours: int = 24
    batch_size: int = 100


class MemoryQualityChecker:
    """Verificador de calidad de entradas de memoria.

    Implementa deduplicación, expiración, scoring de relevancia
    y limpieza periódica para mantener la memoria libre de
    datos irrelevantes o duplicados.
    """

    def __init__(self, policy: Optional[CleanupPolicy] = None) -> None:
        self.policy = policy or CleanupPolicy()
        self._logger = structlog.get_logger()

    def check_quality(
        self,
        content: str,
        metadata: Dict[str, Any],
        access_count: int = 0,
        created_at: Optional[datetime] = None,
    ) -> float:
        """Calculate quality score (0.0 to 1.0) for a memory entry.

        Factors in content length, access count, recency, metadata
        richness, and penalizes generic short content.
        """
        score = 0.0

        # Content length factor
        content_len = len(content)
        if content_len > 200:
            score += 0.3
        elif content_len > 50:
            score += 0.2
        elif content_len < 10:
            score += 0.1

        # Access count factor
        score += min(0.3, access_count * 0.05)

        # Recency factor
        if created_at is not None:
            now = datetime.now()
            days_since_creation = (now - created_at).days
            if days_since_creation <= 7:
                score += 0.2
            elif days_since_creation <= 30:
                score += 0.1

        # Has metadata type
        if "type" in metadata:
            score += 0.1

        # Penalize generic content (all lowercase and very short)
        if content == content.lower() and content_len < 20:
            score -= 0.3

        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        return score

    def classify_quality(self, score: float) -> QualityScore:
        """Classify a quality score into a QualityScore enum value."""
        if score >= 0.8:
            return QualityScore.HIGH
        elif score >= 0.5:
            return QualityScore.MEDIUM
        elif score >= 0.3:
            return QualityScore.LOW
        else:
            return QualityScore.IRRELEVANT

    def is_duplicate(self, content: str, existing_contents: List[str]) -> bool:
        """Check if content is likely a duplicate of existing entries.

        Uses normalization and substring/overlap analysis to detect
        duplicate or near-duplicate content.
        """
        # Normalize content: lowercase, strip, remove extra spaces
        normalized = " ".join(content.lower().strip().split())
        normalized_prefix = normalized[:100]

        for existing in existing_contents:
            normalized_existing = " ".join(existing.lower().strip().split())
            normalized_existing_prefix = normalized_existing[:100]

            # Exact match on first 100 chars
            if normalized_prefix == normalized_existing_prefix:
                return True

            # Content is substring of existing
            if normalized in normalized_existing:
                return True

            # Existing is substring of content with >90% overlap
            if normalized_existing in normalized:
                if len(normalized) > 0:
                    overlap_ratio = len(normalized_existing) / len(normalized)
                    if overlap_ratio > 0.9:
                        return True

        return False

    def should_expire(
        self,
        created_at: datetime,
        memory_type: str = "",
        last_accessed: Optional[datetime] = None,
    ) -> bool:
        """Check if an entry should be expired based on policy.

        Episodic memories have a shorter TTL. If last_accessed is
        provided, it is used instead of created_at for the comparison.
        """
        now = datetime.now()

        if memory_type == "episodic":
            expiry_days = self.policy.expire_episodic_after_days
        else:
            expiry_days = self.policy.expire_after_days

        reference_date = last_accessed if last_accessed is not None else created_at
        days_since = (now - reference_date).days

        return days_since > expiry_days

    def get_entries_to_cleanup(self, entries: List[Dict[str, Any]]) -> List[str]:
        """Determine which entries should be cleaned up.

        Entries are marked for removal if they have a score below the
        minimum, are expired, or are duplicates of a higher-scored entry.
        """
        entry_ids_to_remove: List[str] = []
        kept_contents: List[str] = []

        # Sort by score descending so higher-scored entries are kept first
        sorted_entries = sorted(entries, key=lambda e: e.get("score", 0.0), reverse=True)

        for entry in sorted_entries:
            entry_id = entry.get("entry_id", "")
            content = entry.get("content", "")
            score = entry.get("score", 0.0)
            memory_type = entry.get("memory_type", "")
            created_at = entry.get("created_at")
            metadata = entry.get("metadata", {})

            should_remove = False

            # Check if score is below minimum
            if score < self.policy.min_relevance_score:
                self._logger.debug(
                    "entry_below_min_score",
                    entry_id=entry_id,
                    score=score,
                    min_score=self.policy.min_relevance_score,
                )
                should_remove = True

            # Check if expired
            if not should_remove and created_at is not None:
                if self.should_expire(created_at, memory_type):
                    self._logger.debug(
                        "entry_expired",
                        entry_id=entry_id,
                        memory_type=memory_type,
                    )
                    should_remove = True

            # Check if duplicate of a kept entry
            if not should_remove and self.is_duplicate(content, kept_contents):
                self._logger.debug(
                    "entry_duplicate",
                    entry_id=entry_id,
                )
                should_remove = True

            if should_remove:
                entry_ids_to_remove.append(entry_id)
            else:
                kept_contents.append(content)

        return entry_ids_to_remove

    def deduplicate_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate entries, keeping the one with higher score.

        Groups entries by similarity and retains the best-scoring entry
        from each group.
        """
        result: List[Dict[str, Any]] = []
        duplicate_groups: List[List[Dict[str, Any]]] = []

        for entry in entries:
            content = entry.get("content", "")
            placed = False

            for group in duplicate_groups:
                representative = group[0]
                if self.is_duplicate(content, [representative.get("content", "")]):
                    group.append(entry)
                    placed = True
                    break

            if not placed:
                duplicate_groups.append([entry])

        # From each group, keep the one with highest score
        for group in duplicate_groups:
            best = max(group, key=lambda e: e.get("score", 0.0))
            result.append(best)

        return result

    def score_entry(
        self,
        content: str,
        metadata: Dict[str, Any],
        access_count: int = 0,
        created_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Full scoring of an entry.

        Returns quality score, classification, duplication status,
        expiration status, and a keep/remove/review recommendation.
        """
        quality_score = self.check_quality(content, metadata, access_count, created_at)
        quality_level = self.classify_quality(quality_score)

        # Check for duplicates if existing contents provided in metadata
        existing_contents = metadata.get("existing_contents", [])
        is_dup = self.is_duplicate(content, existing_contents) if existing_contents else False

        # Check expiration
        should_exp = False
        if created_at is not None:
            memory_type = metadata.get("type", "")
            should_exp = self.should_expire(created_at, memory_type)

        # Determine recommendation
        if should_exp or quality_level == QualityScore.IRRELEVANT:
            recommendation = "remove"
        elif quality_level == QualityScore.LOW or is_dup:
            recommendation = "review"
        else:
            recommendation = "keep"

        return {
            "quality_score": quality_score,
            "quality_level": quality_level,
            "is_duplicate": is_dup,
            "should_expire": should_exp,
            "recommendation": recommendation,
        }


class MemoryCleanupTask:
    """Tarea de limpieza de memoria.

    Ejecuta la limpieza periódica de la memoria vectorial,
    eliminando entradas expiradas, irrelevantes y duplicadas.
    """

    def __init__(
        self,
        quality_checker: Optional[MemoryQualityChecker] = None,
        memory_store: Any = None,
    ) -> None:
        self.quality_checker = quality_checker or MemoryQualityChecker()
        self.memory_store = memory_store
        self._logger = structlog.get_logger()
        self._total_cleanups: int = 0
        self._last_cleanup: Optional[datetime] = None
        self._entries_removed_total: int = 0
        self._scheduled_interval_hours: int = 24

    async def run_cleanup(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Run cleanup on memory store.

        Scans entries, identifies those to remove based on quality
        policy, and deletes them. Returns a summary of actions taken.
        """
        result: Dict[str, Any] = {
            "entries_scanned": 0,
            "entries_removed": 0,
            "space_freed_estimate": 0,
            "by_reason": {
                "expired": 0,
                "low_quality": 0,
                "duplicate": 0,
            },
        }

        if self.memory_store is None:
            self._logger.warning("memory_store_not_available")
            return result

        # Get entries from memory store
        try:
            if project_id is not None and hasattr(self.memory_store, "get_entries_by_project"):
                entries = await self.memory_store.get_entries_by_project(project_id)
            elif hasattr(self.memory_store, "get_all_entries"):
                entries = await self.memory_store.get_all_entries()
            else:
                self._logger.warning("memory_store_missing_methods")
                return result
        except Exception as e:
            self._logger.error("memory_store_access_error", error=str(e))
            return result

        if not entries:
            return result

        result["entries_scanned"] = len(entries)

        # Identify entries to remove
        entries_to_remove_ids = self.quality_checker.get_entries_to_cleanup(entries)

        # Categorize reasons for removal
        entries_by_id = {e.get("entry_id"): e for e in entries}
        for entry_id in entries_to_remove_ids:
            entry = entries_by_id.get(entry_id, {})
            score = entry.get("score", 0.0)
            memory_type = entry.get("memory_type", "")
            created_at = entry.get("created_at")
            content = entry.get("content", "")
            metadata = entry.get("metadata", {})

            # Determine primary reason
            if score < self.quality_checker.policy.min_relevance_score:
                result["by_reason"]["low_quality"] += 1
            elif created_at is not None and self.quality_checker.should_expire(
                created_at, memory_type
            ):
                result["by_reason"]["expired"] += 1
            else:
                result["by_reason"]["duplicate"] += 1

        # Remove entries from store
        for entry_id in entries_to_remove_ids:
            try:
                if hasattr(self.memory_store, "delete_entry"):
                    await self.memory_store.delete_entry(entry_id)
                elif hasattr(self.memory_store, "remove_entry"):
                    await self.memory_store.remove_entry(entry_id)
            except Exception as e:
                self._logger.error("entry_removal_error", entry_id=entry_id, error=str(e))

        result["entries_removed"] = len(entries_to_remove_ids)
        result["space_freed_estimate"] = len(entries_to_remove_ids) * 500

        # Update internal stats
        self._total_cleanups += 1
        self._last_cleanup = datetime.now()
        self._entries_removed_total += len(entries_to_remove_ids)

        self._logger.info(
            "cleanup_completed",
            entries_scanned=result["entries_scanned"],
            entries_removed=result["entries_removed"],
            by_reason=result["by_reason"],
        )

        return result

    async def schedule_cleanup(self, interval_hours: int = 24) -> None:
        """Schedule periodic cleanup (actual scheduling handled externally).

        Stores the desired interval and logs the scheduling intent.
        The external scheduler is responsible for invoking run_cleanup.
        """
        self._scheduled_interval_hours = interval_hours
        self._logger.info(
            "cleanup_scheduled",
            interval_hours=interval_hours,
            message="Cleanup has been scheduled. Actual scheduling is handled externally.",
        )

    def get_cleanup_stats(self) -> Dict[str, Any]:
        """Return cleanup statistics."""
        return {
            "total_cleanups": self._total_cleanups,
            "last_cleanup": self._last_cleanup,
            "entries_removed_total": self._entries_removed_total,
        }
