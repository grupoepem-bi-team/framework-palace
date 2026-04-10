"""
Palace Framework - Memory Store Backends

This module provides concrete implementations of the :class:`MemoryBase`
interface for different storage backends:

- **SQLiteMemoryStore**: Local SQLite-backed storage for development and
  single-instance deployments. Uses ``aiosqlite`` when available, falling
  back to synchronous ``sqlite3`` with ``asyncio.run_in_executor()``.
- **ChromaMemoryStore**: ChromaDB-backed vector store (stub – not yet
  implemented).
- **ZepMemoryStore**: Zep cloud-backed store (stub – not yet implemented).

Usage::

    from palace.memory.stores import SQLiteMemoryStore
    from palace.memory.base import MemoryEntry, SearchQuery

    store = SQLiteMemoryStore("memories.db")
    await store.initialize()

    entry_id = await store.store(MemoryEntry(content="Hello", project_id="demo"))
    results = await store.search(SearchQuery(query="hello"))

    await store.close()
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from palace.memory.base import (
    MemoryBase,
    MemoryEntry,
    MemoryPriority,
    MemoryType,
    SearchQuery,
    SearchResult,
)

try:
    import aiosqlite  # type: ignore[import-untyped]

    _HAS_AIOSQLITE = True
except ImportError:
    aiosqlite = None  # type: ignore[assignment]
    _HAS_AIOSQLITE = False

logger = __import__("structlog").get_logger()


# ---------------------------------------------------------------------------
# SQL DDL
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_entries (
    id            TEXT PRIMARY KEY,
    project_id    TEXT    NOT NULL DEFAULT '',
    content       TEXT    NOT NULL DEFAULT '',
    memory_type   TEXT    NOT NULL DEFAULT 'episodic',
    metadata      TEXT    NOT NULL DEFAULT '{}',
    timestamp     TEXT    NOT NULL,
    embedding     BLOB,
    source        TEXT    NOT NULL DEFAULT 'unknown',
    source_id     TEXT,
    expires_at    TEXT,
    access_count  INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT,
    priority      INTEGER NOT NULL DEFAULT 5
)
"""

_CREATE_PROJECT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_entries_project_id
ON memory_entries(project_id)
"""

_CREATE_TYPE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type
ON memory_entries(memory_type)
"""


# ---------------------------------------------------------------------------
# SQLiteMemoryStore
# ---------------------------------------------------------------------------


class SQLiteMemoryStore(MemoryBase):
    """SQLite-backed memory store for local development.

    This implementation stores :class:`MemoryEntry` instances in a local
    SQLite database file.  It is suitable for development, testing, and
    single-instance deployments that do not require distributed storage.

    **Search** is performed using SQLite's ``LIKE`` operator for basic
    substring matching on the ``content`` column.  Vector / semantic search
    is *not* supported – callers that need semantic retrieval should use
    :class:`ChromaMemoryStore` or :class:`ZepMemoryStore` instead.

    If the ``aiosqlite`` package is installed, it is used for native async
    I/O.  Otherwise, synchronous ``sqlite3`` calls are wrapped with
    ``asyncio.get_running_loop().run_in_executor()`` so that the public
    API remains fully asynchronous.

    Args:
        path: Filesystem path to the SQLite database file.
            Use ``":memory:"`` for an ephemeral in-memory database.

    Example::

        store = SQLiteMemoryStore("memories.db")
        await store.initialize()
        try:
            eid = await store.store(MemoryEntry(content="note", project_id="p1"))
            entry = await store.retrieve(eid)
        finally:
            await store.close()
    """

    def __init__(self, path: str) -> None:
        self._path: str = path
        self._db: Optional[Any] = None
        self._use_aiosqlite: bool = _HAS_AIOSQLITE

    # ------------------------------------------------------------------
    # Internal: row ↔ entry conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _entry_to_row(entry: MemoryEntry) -> tuple:
        """Serialise a :class:`MemoryEntry` into a row tuple for INSERT."""
        embedding_data: Optional[bytes] = (
            json.dumps(entry.embedding).encode("utf-8") if entry.embedding is not None else None
        )
        metadata_json: str = json.dumps(entry.metadata) if entry.metadata else "{}"
        return (
            entry.entry_id,
            entry.project_id,
            entry.content,
            entry.memory_type.value,
            metadata_json,
            entry.created_at.isoformat(),
            embedding_data,
            entry.source,
            entry.source_id,
            entry.expires_at.isoformat() if entry.expires_at else None,
            entry.access_count,
            entry.last_accessed.isoformat() if entry.last_accessed else None,
            entry.priority.value,
        )

    @staticmethod
    def _row_to_entry(row: tuple) -> MemoryEntry:
        """Deserialise a database row tuple into a :class:`MemoryEntry`."""
        (
            entry_id,
            project_id,
            content,
            memory_type,
            metadata_json,
            timestamp,
            embedding_data,
            source,
            source_id,
            expires_at,
            access_count,
            last_accessed,
            priority,
        ) = row

        embedding: Optional[List[float]] = (
            json.loads(embedding_data.decode("utf-8")) if embedding_data is not None else None
        )
        metadata: Dict[str, Any] = json.loads(metadata_json) if metadata_json else {}

        return MemoryEntry(
            entry_id=entry_id,
            project_id=project_id,
            content=content,
            memory_type=MemoryType(memory_type),
            metadata=metadata,
            created_at=datetime.fromisoformat(timestamp),
            embedding=embedding,
            source=source or "unknown",
            source_id=source_id,
            expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
            access_count=access_count or 0,
            last_accessed=datetime.fromisoformat(last_accessed) if last_accessed else None,
            priority=MemoryPriority(priority) if priority is not None else MemoryPriority.NORMAL,
        )

    # ------------------------------------------------------------------
    # Internal: sync executor helper
    # ------------------------------------------------------------------

    async def _run_sync(self, func):  # type: ignore[no-untyped-def]
        """Run *func* in the default executor so the event loop is not blocked."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func)

    # ------------------------------------------------------------------
    # MemoryBase implementation
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Create the database file and ensure the schema exists."""
        if self._use_aiosqlite:
            self._db = await aiosqlite.connect(self._path)
            await self._db.execute(_CREATE_TABLE_SQL)
            await self._db.execute(_CREATE_PROJECT_INDEX_SQL)
            await self._db.execute(_CREATE_TYPE_INDEX_SQL)
            await self._db.commit()
            logger.info(
                "sqlite_memory_store.initialized",
                path=self._path,
                backend="aiosqlite",
            )
        else:
            self._db = sqlite3.connect(self._path, check_same_thread=False)
            self._db.execute(_CREATE_TABLE_SQL)
            self._db.execute(_CREATE_PROJECT_INDEX_SQL)
            self._db.execute(_CREATE_TYPE_INDEX_SQL)
            self._db.commit()
            logger.info(
                "sqlite_memory_store.initialized",
                path=self._path,
                backend="sqlite3",
            )

    async def close(self) -> None:
        """Flush and close the database connection."""
        if self._db is None:
            return
        if self._use_aiosqlite:
            await self._db.close()
        else:
            await self._run_sync(self._db.close)
        self._db = None
        logger.info("sqlite_memory_store.closed")

    async def store(self, entry: MemoryEntry) -> str:
        """Store a single memory entry and return its ID."""
        row = self._entry_to_row(entry)
        sql = (
            "INSERT OR REPLACE INTO memory_entries "
            "(id, project_id, content, memory_type, metadata, timestamp, "
            "embedding, source, source_id, expires_at, access_count, "
            "last_accessed, priority) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        if self._use_aiosqlite:
            await self._db.execute(sql, row)
            await self._db.commit()
        else:
            await self._run_sync(lambda: self._db.execute(sql, row))
            await self._run_sync(self._db.commit)
        return entry.entry_id

    async def store_batch(self, entries: List[MemoryEntry]) -> List[str]:
        """Store multiple memory entries and return their IDs."""
        if not entries:
            return []
        rows = [self._entry_to_row(e) for e in entries]
        sql = (
            "INSERT OR REPLACE INTO memory_entries "
            "(id, project_id, content, memory_type, metadata, timestamp, "
            "embedding, source, source_id, expires_at, access_count, "
            "last_accessed, priority) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )
        if self._use_aiosqlite:
            await self._db.executemany(sql, rows)
            await self._db.commit()
        else:
            await self._run_sync(lambda: self._db.executemany(sql, rows))
            await self._run_sync(self._db.commit)
        return [e.entry_id for e in entries]

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by its unique ID."""
        sql = "SELECT * FROM memory_entries WHERE id = ?"
        if self._use_aiosqlite:
            async with self._db.execute(sql, (entry_id,)) as cursor:
                row = await cursor.fetchone()
        else:
            row = await self._run_sync(lambda: self._db.execute(sql, (entry_id,)).fetchone())
        if row is None:
            return None
        return self._row_to_entry(row)

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Search for memory entries using basic text matching.

        This implementation uses SQLite's ``LIKE`` operator for substring
        matching on the ``content`` column.  Vector / semantic search is
        **not** supported – if the query strategy requires embeddings,
        the method falls back to keyword-based search.

        Metadata filters are applied using SQLite's ``json_extract``
        function.
        """
        if not query.query:
            return []

        conditions: List[str] = []
        params: List[Any] = []

        # --- text search on content -------------------------------------------
        conditions.append("content LIKE ?")
        params.append(f"%{query.query}%")

        # --- project scope ----------------------------------------------------
        if query.project_id is not None:
            conditions.append("project_id = ?")
            params.append(query.project_id)

        # --- memory type filter -----------------------------------------------
        if query.memory_types:
            placeholders = ",".join("?" * len(query.memory_types))
            conditions.append(f"memory_type IN ({placeholders})")
            params.extend(mt.value for mt in query.memory_types)

        # --- expiry filter ----------------------------------------------------
        if not query.include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(datetime.utcnow().isoformat())

        # --- metadata filters via json_extract --------------------------------
        for key, value in query.filters.items():
            json_path = f"$.{key}"
            conditions.append("json_extract(metadata, ?) = ?")
            params.append(json_path)
            params.append(value if not isinstance(value, bool) else int(value))

        where_clause = " AND ".join(conditions)
        sql = f"SELECT * FROM memory_entries WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?"
        params.append(query.top_k)

        # --- execute ----------------------------------------------------------
        if self._use_aiosqlite:
            async with self._db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
        else:
            rows = await self._run_sync(lambda: self._db.execute(sql, params).fetchall())

        # --- build results ----------------------------------------------------
        results: List[SearchResult] = []
        query_lower = query.query.lower()
        for row in rows:
            entry = self._row_to_entry(row)
            # Basic relevance scoring: exact case-insensitive match → 1.0,
            # LIKE match → 0.5
            score = 1.0 if query_lower in entry.content.lower() else 0.5
            if score < query.min_score:
                continue
            results.append(
                SearchResult(
                    entry=entry,
                    score=score,
                    highlights=[query.query],
                )
            )
        return results

    async def delete(self, entry_id: str) -> bool:
        """Delete a single memory entry by ID."""
        sql = "DELETE FROM memory_entries WHERE id = ?"
        if self._use_aiosqlite:
            cursor = await self._db.execute(sql, (entry_id,))
            await self._db.commit()
            deleted = cursor.rowcount > 0
        else:
            cursor = await self._run_sync(lambda: self._db.execute(sql, (entry_id,)))
            await self._run_sync(self._db.commit)
            deleted = cursor.rowcount > 0
        return deleted

    async def delete_batch(self, entry_ids: List[str]) -> int:
        """Delete multiple memory entries and return the number removed."""
        if not entry_ids:
            return 0
        placeholders = ",".join("?" * len(entry_ids))
        sql = f"DELETE FROM memory_entries WHERE id IN ({placeholders})"
        if self._use_aiosqlite:
            cursor = await self._db.execute(sql, entry_ids)
            await self._db.commit()
            return cursor.rowcount
        else:
            cursor = await self._run_sync(lambda: self._db.execute(sql, entry_ids))
            await self._run_sync(self._db.commit)
            return cursor.rowcount

    async def delete_by_project(self, project_id: str) -> int:
        """Delete all entries belonging to *project_id*."""
        sql = "DELETE FROM memory_entries WHERE project_id = ?"
        if self._use_aiosqlite:
            cursor = await self._db.execute(sql, (project_id,))
            await self._db.commit()
            return cursor.rowcount
        else:
            cursor = await self._run_sync(lambda: self._db.execute(sql, (project_id,)))
            await self._run_sync(self._db.commit)
            return cursor.rowcount

    async def count(self, project_id: Optional[str] = None) -> int:
        """Count entries, optionally scoped to a project."""
        if project_id is not None:
            sql = "SELECT COUNT(*) FROM memory_entries WHERE project_id = ?"
            params: tuple = (project_id,)
        else:
            sql = "SELECT COUNT(*) FROM memory_entries"
            params = ()

        if self._use_aiosqlite:
            async with self._db.execute(sql, params) as cursor:
                row = await cursor.fetchone()
        else:
            row = await self._run_sync(lambda: self._db.execute(sql, params).fetchone())
        return row[0] if row else 0

    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        """Clear entries, optionally filtered by *memory_type*."""
        if memory_type is not None:
            sql = "DELETE FROM memory_entries WHERE memory_type = ?"
            params: tuple = (memory_type.value,)
        else:
            sql = "DELETE FROM memory_entries"
            params = ()

        if self._use_aiosqlite:
            cursor = await self._db.execute(sql, params)
            await self._db.commit()
            return cursor.rowcount
        else:
            cursor = await self._run_sync(lambda: self._db.execute(sql, params))
            await self._run_sync(self._db.commit)
            return cursor.rowcount


# ---------------------------------------------------------------------------
# ChromaMemoryStore (stub)
# ---------------------------------------------------------------------------


class ChromaMemoryStore(MemoryBase):
    """ChromaDB-backed memory store (stub).

    This class is a placeholder for a future ChromaDB implementation.
    All data-manipulation methods raise :class:`NotImplementedError`.
    Only :meth:`initialize` and :meth:`close` are functional (no-ops).

    Args:
        collection_name: Name of the ChromaDB collection to use.
    """

    def __init__(self, collection_name: str) -> None:
        self._collection_name = collection_name

    async def initialize(self) -> None:
        """No-op placeholder for future ChromaDB initialisation."""

    async def close(self) -> None:
        """No-op placeholder for future ChromaDB teardown."""

    async def store(self, entry: MemoryEntry) -> str:
        raise NotImplementedError("ChromaMemoryStore.store() is not yet implemented")

    async def store_batch(self, entries: List[MemoryEntry]) -> List[str]:
        raise NotImplementedError("ChromaMemoryStore.store_batch() is not yet implemented")

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        raise NotImplementedError("ChromaMemoryStore.retrieve() is not yet implemented")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        raise NotImplementedError("ChromaMemoryStore.search() is not yet implemented")

    async def delete(self, entry_id: str) -> bool:
        raise NotImplementedError("ChromaMemoryStore.delete() is not yet implemented")

    async def delete_batch(self, entry_ids: List[str]) -> int:
        raise NotImplementedError("ChromaMemoryStore.delete_batch() is not yet implemented")

    async def delete_by_project(self, project_id: str) -> int:
        raise NotImplementedError("ChromaMemoryStore.delete_by_project() is not yet implemented")

    async def count(self, project_id: Optional[str] = None) -> int:
        raise NotImplementedError("ChromaMemoryStore.count() is not yet implemented")

    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        raise NotImplementedError("ChromaMemoryStore.clear() is not yet implemented")


# ---------------------------------------------------------------------------
# ZepMemoryStore (stub)
# ---------------------------------------------------------------------------


class ZepMemoryStore(MemoryBase):
    """Zep cloud-backed memory store (stub).

    This class is a placeholder for a future Zep implementation.
    All data-manipulation methods raise :class:`NotImplementedError`.
    Only :meth:`initialize` and :meth:`close` are functional (no-ops).

    Args:
        api_url: Base URL of the Zep API server.
        api_key: Optional API key for authentication.
    """

    def __init__(self, api_url: str, api_key: Optional[str] = None) -> None:
        self._api_url = api_url
        self._api_key = api_key

    async def initialize(self) -> None:
        """No-op placeholder for future Zep initialisation."""

    async def close(self) -> None:
        """No-op placeholder for future Zep teardown."""

    async def store(self, entry: MemoryEntry) -> str:
        raise NotImplementedError("ZepMemoryStore.store() is not yet implemented")

    async def store_batch(self, entries: List[MemoryEntry]) -> List[str]:
        raise NotImplementedError("ZepMemoryStore.store_batch() is not yet implemented")

    async def retrieve(self, entry_id: str) -> Optional[MemoryEntry]:
        raise NotImplementedError("ZepMemoryStore.retrieve() is not yet implemented")

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        raise NotImplementedError("ZepMemoryStore.search() is not yet implemented")

    async def delete(self, entry_id: str) -> bool:
        raise NotImplementedError("ZepMemoryStore.delete() is not yet implemented")

    async def delete_batch(self, entry_ids: List[str]) -> int:
        raise NotImplementedError("ZepMemoryStore.delete_batch() is not yet implemented")

    async def delete_by_project(self, project_id: str) -> int:
        raise NotImplementedError("ZepMemoryStore.delete_by_project() is not yet implemented")

    async def count(self, project_id: Optional[str] = None) -> int:
        raise NotImplementedError("ZepMemoryStore.count() is not yet implemented")

    async def clear(self, memory_type: Optional[MemoryType] = None) -> int:
        raise NotImplementedError("ZepMemoryStore.clear() is not yet implemented")
