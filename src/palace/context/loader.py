"""
Cargador de Contexto de Proyecto - Palace Framework

Este módulo se encarga de cargar y parsear los archivos markdown del
directorio /ai_context/ de un proyecto para construir el contexto que
será utilizado por los agentes.

Archivos soportados:
    - architecture.md: Documentación de arquitectura
    - stack.md: Stack tecnológico del proyecto
    - conventions.md: Convenciones de código
    - decisions.md: Registros de Decisiones de Arquitectura (ADR)
    - constraints.md: Restricciones del proyecto

El cargador opera de forma asíncrona y mantiene una caché interna
para evitar lecturas redundantes del sistema de archivos.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import structlog

from palace.context.types import ContextEntry, ContextType, ProjectConfig

logger = structlog.get_logger()


class ProjectLoader:
    """Cargador de contexto de proyecto desde archivos markdown.

    Carga y parsea los archivos del directorio /ai_context/ de un proyecto
    para construir el contexto que será utilizado por los agentes.
    """

    _FILE_MAPPING: Dict[str, ContextType] = {
        "architecture.md": ContextType.ARCHITECTURE,
        "stack.md": ContextType.STACK,
        "conventions.md": ContextType.CONVENTIONS,
        "decisions.md": ContextType.DECISIONS,
        "constraints.md": ContextType.CONSTRAINTS,
    }

    def __init__(
        self,
        project_path: Path,
        context_dir_name: str = "ai_context",
        cache_loaded: bool = True,
        watch_enabled: bool = False,
    ) -> None:
        """Initialize the ProjectLoader.

        Args:
            project_path: Root path of the project.
            context_dir_name: Name of context directory.
            cache_loaded: Whether to cache loaded files.
            watch_enabled: Whether to watch for file changes.
        """
        self._project_path = project_path
        self._context_dir_name = context_dir_name
        self._cache_loaded = cache_loaded
        self._watch_enabled = watch_enabled

        # Cache storage
        self._cache: Dict[str, ContextEntry] = {}
        self._raw_cache: Dict[str, str] = {}
        self._project_config: Optional[ProjectConfig] = None

    @property
    def context_path(self) -> Path:
        """Returns the path to the context directory."""
        return self._project_path / self._context_dir_name

    @property
    def is_loaded(self) -> bool:
        """Returns True if context has been loaded."""
        return self._project_config is not None

    @property
    def loaded_files(self) -> List[str]:
        """Returns list of loaded file names."""
        return list(self._cache.keys())

    # -------------------------------------------------------------------------
    # Public Async Methods
    # -------------------------------------------------------------------------

    async def load(self) -> ProjectConfig:
        """Main entry point. Loads all context files from the project.

        If cache_loaded is enabled and context has already been loaded,
        returns the cached ProjectConfig. Otherwise, loads all files from
        the ai_context directory, parses them, and builds a ProjectConfig.

        Returns:
            ProjectConfig with all loaded context data.
        """
        if self._cache_loaded and self._project_config is not None:
            logger.debug(
                "context_already_loaded",
                project=str(self._project_path),
            )
            return self._project_config

        # Ensure the context directory exists
        try:
            if not self.context_path.exists():
                self.context_path.mkdir(parents=True, exist_ok=True)
                logger.info(
                    "context_directory_created",
                    path=str(self.context_path),
                )
        except OSError as exc:
            logger.error(
                "failed_to_create_context_directory",
                path=str(self.context_path),
                error=str(exc),
            )
            return self._build_empty_config()

        # Load all files
        entries = await self._load_all_files()

        # Parse the stack content
        stack_content = self._raw_cache.get("stack.md", "")
        parsed_stack: Dict[str, str] = {}
        if stack_content:
            parsed_stack = self._parse_stack_content(stack_content)

        # Extract conventions, decisions, and constraints titles from entries
        conventions = self._extract_titles_by_type(entries, ContextType.CONVENTIONS)
        decisions = self._extract_titles_by_type(entries, ContextType.DECISIONS)
        constraints = self._extract_titles_by_type(entries, ContextType.CONSTRAINTS)

        # Build the description from architecture entry if available
        architecture_entry = next(
            (e for e in entries if e.context_type == ContextType.ARCHITECTURE),
            None,
        )
        description = architecture_entry.title if architecture_entry else None

        config = ProjectConfig(
            project_id=str(self._project_path),
            name=self._project_path.name,
            description=description,
            root_path=self._project_path,
            context_path=self.context_path,
            stack=parsed_stack,
            conventions=conventions,
            decisions=decisions,
            constraints=constraints,
            last_loaded=datetime.utcnow(),
        )

        self._project_config = config

        logger.info(
            "project_context_loaded",
            project=config.name,
            files_loaded=len(self._cache),
            stack_items=len(parsed_stack),
        )

        return config

    async def load_file(self, filename: str) -> Optional[ContextEntry]:
        """Load a single file by name.

        Args:
            filename: Name of the file to load (e.g. 'architecture.md').

        Returns:
            A ContextEntry if the file exists, None otherwise.
        """
        context_type = self._FILE_MAPPING.get(filename)
        if context_type is None:
            logger.warning(
                "unknown_context_file",
                filename=filename,
                known_files=list(self._FILE_MAPPING.keys()),
            )
            return None

        filepath = self.context_path / filename
        content = await self._read_file(filepath)

        if content is None:
            return None

        # Store in raw cache
        if self._cache_loaded:
            self._raw_cache[filename] = content

        entry = self._parse_markdown(content, context_type, filename)

        # Store in entry cache
        if self._cache_loaded:
            self._cache[filename] = entry

        logger.debug(
            "context_file_loaded",
            filename=filename,
            context_type=context_type.value,
        )

        return entry

    async def reload(self) -> ProjectConfig:
        """Force reload all context files (clears cache first).

        Invalidates all cached data and performs a fresh load
        of all context files.

        Returns:
            ProjectConfig with freshly loaded context data.
        """
        logger.info(
            "reloading_project_context",
            project=str(self._project_path),
        )
        self.invalidate_cache()
        return await self.load()

    async def get_file_content(self, filename: str) -> Optional[str]:
        """Get raw content of a context file.

        Returns the raw markdown string if the file exists,
        or None if it doesn't.

        Args:
            filename: Name of the file to read.

        Returns:
            Raw markdown content as a string, or None.
        """
        # Check raw cache first
        if self._cache_loaded and filename in self._raw_cache:
            return self._raw_cache[filename]

        filepath = self.context_path / filename
        content = await self._read_file(filepath)

        if content is not None and self._cache_loaded:
            self._raw_cache[filename] = content

        return content

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def invalidate_cache(self) -> None:
        """Clear all caches."""
        self._cache.clear()
        self._raw_cache.clear()
        self._project_config = None
        logger.debug("context_cache_invalidated")

    def invalidate_file(self, filename: str) -> None:
        """Remove a specific file from cache.

        Args:
            filename: Name of the file to remove from cache.
        """
        self._cache.pop(filename, None)
        self._raw_cache.pop(filename, None)
        logger.debug(
            "context_file_cache_invalidated",
            filename=filename,
        )

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics.

        Returns:
            Dictionary with number of cached files, total tokens,
            and list of cached file names.
        """
        total_tokens = sum(entry.token_count for entry in self._cache.values())
        return {
            "cached_files": len(self._cache),
            "total_tokens": total_tokens,
            "files": list(self._cache.keys()),
        }

    # -------------------------------------------------------------------------
    # Private Async Methods
    # -------------------------------------------------------------------------

    async def _load_all_files(self) -> List[ContextEntry]:
        """Load all context files from the mapping.

        Iterates over _FILE_MAPPING and attempts to load each file.
        Files that are not found are skipped silently.

        Returns:
            List of successfully loaded ContextEntry objects.
        """
        entries: List[ContextEntry] = []
        loaded_names: List[str] = []
        skipped_names: List[str] = []

        for filename, _ in self._FILE_MAPPING.items():
            try:
                entry = await self.load_file(filename)
                if entry is not None:
                    entries.append(entry)
                    loaded_names.append(filename)
                else:
                    skipped_names.append(filename)
            except Exception as exc:
                logger.error(
                    "failed_to_load_context_file",
                    filename=filename,
                    error=str(exc),
                )
                skipped_names.append(filename)

        logger.info(
            "context_files_summary",
            loaded=loaded_names,
            skipped=skipped_names,
            total=len(self._FILE_MAPPING),
        )

        return entries

    async def _read_file(self, filepath: Path) -> Optional[str]:
        """Read file content asynchronously.

        Args:
            filepath: Full path to the file to read.

        Returns:
            File content as string, or None if file not found or unreadable.
        """
        try:
            async with aiofiles.open(filepath, encoding="utf-8") as f:
                content = await f.read()
            return content
        except FileNotFoundError:
            logger.debug(
                "context_file_not_found",
                filepath=str(filepath),
            )
            return None
        except UnicodeDecodeError as exc:
            logger.warning(
                "context_file_unicode_error",
                filepath=str(filepath),
                error=str(exc),
            )
            return None
        except OSError as exc:
            logger.error(
                "context_file_read_error",
                filepath=str(filepath),
                error=str(exc),
            )
            return None

    # -------------------------------------------------------------------------
    # Private Parsing Methods
    # -------------------------------------------------------------------------

    def _parse_markdown(
        self,
        content: str,
        context_type: ContextType,
        filename: str,
    ) -> ContextEntry:
        """Parse markdown content into a structured ContextEntry.

        Extracts the title from the first # heading (or falls back to filename),
        estimates token count, and extracts section headings into metadata.

        Args:
            content: Raw markdown content.
            context_type: The type of context for this file.
            filename: The source filename.

        Returns:
            A ContextEntry with parsed metadata.
        """
        title = self._extract_title(content, filename)
        token_count = self._estimate_tokens(content)
        sections = self._parse_sections(content)

        return ContextEntry(
            context_type=context_type,
            source=filename,
            title=title,
            content=content,
            metadata={
                "sections": sections,
                "filename": filename,
            },
            token_count=token_count,
        )

    def _parse_stack_content(self, content: str) -> Dict[str, str]:
        """Parse the stack.md content to extract technology mappings.

        Looks for patterns like 'Backend: FastAPI' or '- Python/FastAPI'
        in the content and maps them to common keys.

        Args:
            content: Raw markdown content from stack.md.

        Returns:
            Dictionary mapping category keys to technology names.
        """
        stack: Dict[str, str] = {}

        # Mapping of keywords to look for in the content
        key_patterns: Dict[str, List[str]] = {
            "backend": ["backend", "server", "api", "server-side"],
            "frontend": ["frontend", "client", "ui", "client-side", "web"],
            "database": ["database", "db", "storage", "data store"],
            "deployment": ["deployment", "deploy", "hosting", "infrastructure", "ci/cd"],
            "testing": ["testing", "test", "tests"],
            "cache": ["cache", "caching", "redis"],
            "message_queue": ["message queue", "queue", "messaging", "broker"],
        }

        # Strategy 1: Look for "Key: Value" patterns (e.g. "Backend: FastAPI")
        key_value_pattern = re.compile(
            r"^\s*([A-Za-z][A-Za-z\s]*?)\s*:\s*(.+?)\s*$",
            re.MULTILINE,
        )
        for match in key_value_pattern.finditer(content):
            key_raw = match.group(1).strip().lower()
            value_raw = match.group(2).strip()

            # Skip if value looks like a URL or is too long
            if len(value_raw) > 80 or value_raw.startswith("http"):
                continue

            # Map the key to a canonical category
            for canonical_key, keywords in key_patterns.items():
                if any(kw in key_raw for kw in keywords):
                    if canonical_key not in stack:
                        # Clean the value - take the primary technology
                        clean_value = self._clean_tech_value(value_raw)
                        if clean_value:
                            stack[canonical_key] = clean_value
                    break

        # Strategy 2: Look for "- Technology" patterns under section headings
        section_content_map = self._extract_section_content(content)
        for section_title, section_text in section_content_map.items():
            section_lower = section_title.lower()
            canonical = None
            for canonical_key, keywords in key_patterns.items():
                if any(kw in section_lower for kw in keywords):
                    canonical = canonical_key
                    break

            if canonical and canonical not in stack:
                # Find list items in the section
                items = re.findall(r"^\s*[-*]\s+(.+?)\s*$", section_text, re.MULTILINE)
                if items:
                    first_item = items[0]
                    clean_value = self._clean_tech_value(first_item)
                    if clean_value:
                        stack[canonical] = clean_value

        return stack

    def _parse_sections(self, content: str) -> List[str]:
        """Extract all ## headings from markdown.

        Args:
            content: Raw markdown content.

        Returns:
            List of section titles (without the ## prefix).
        """
        sections: List[str] = []
        for match in re.finditer(r"^##\s+(.+?)\s*$", content, re.MULTILINE):
            sections.append(match.group(1).strip())
        return sections

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation.

        Uses a simple heuristic: word count multiplied by 1.3
        to account for sub-word tokens.

        Args:
            text: Text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        return int(len(text.split()) * 1.3)

    def _extract_title(self, content: str, fallback: str) -> str:
        """Find first # heading and return the title text.

        Args:
            content: Raw markdown content.
            fallback: Fallback title if no heading is found.

        Returns:
            The title string extracted from the first h1 heading,
            or the fallback value.
        """
        match = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return fallback

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    def _extract_titles_by_type(
        self,
        entries: List[ContextEntry],
        context_type: ContextType,
    ) -> List[str]:
        """Extract titles from entries matching a given context type.

        Also includes section headings from the entry metadata as
        individual items.

        Args:
            entries: List of context entries to search.
            context_type: The context type to filter by.

        Returns:
            List of section titles found in entries of the given type.
        """
        titles: List[str] = []
        for entry in entries:
            if entry.context_type == context_type:
                sections = entry.metadata.get("sections", [])
                if sections:
                    titles.extend(sections)
        return titles

    def _clean_tech_value(self, value: str) -> str:
        """Clean a technology value string.

        Removes common markdown formatting and extracts the
        primary technology name.

        Args:
            value: Raw technology value string.

        Returns:
            Cleaned lowercase technology name.
        """
        # Remove markdown bold/italic
        cleaned = re.sub(r"[*_`]", "", value)
        # Remove parenthetical notes
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)
        # Take first item if slash-separated (e.g. "Python/FastAPI" -> "fastapi")
        parts = cleaned.split("/")
        # Take the last part as the most specific technology
        tech = parts[-1].strip()
        # Take first word if space-separated
        tech = tech.split()[0] if tech.split() else tech
        return tech.lower()

    def _extract_section_content(self, content: str) -> Dict[str, str]:
        """Extract mapping of section titles to their content.

        Args:
            content: Raw markdown content.

        Returns:
            Dictionary mapping section titles to their text content.
        """
        sections: Dict[str, str] = {}
        # Split by ## headings
        parts = re.split(r"^##\s+(.+?)\s*$", content, flags=re.MULTILINE)

        # parts will be: [intro_text, heading1, content1, heading2, content2, ...]
        for i in range(1, len(parts), 2):
            heading = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            sections[heading] = body

        return sections

    def _build_empty_config(self) -> ProjectConfig:
        """Build an empty ProjectConfig when no context can be loaded.

        Returns:
            A ProjectConfig with empty/default values.
        """
        return ProjectConfig(
            project_id=str(self._project_path),
            name=self._project_path.name,
            description=None,
            root_path=self._project_path,
            context_path=self.context_path,
            stack={},
            conventions=[],
            decisions=[],
            constraints=[],
            last_loaded=datetime.utcnow(),
        )
