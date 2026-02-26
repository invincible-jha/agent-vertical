"""Knowledge base abstractions for domain-specific agent grounding.

Provides an abstract base class :class:`KnowledgeBase` and a concrete
:class:`InMemoryKB` implementation backed by a plain Python dict.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class KnowledgeEntry:
    """A single entry in the knowledge base.

    Attributes
    ----------
    entry_id:
        Unique identifier for this entry.
    title:
        Short human-readable title.
    content:
        Full text content of the entry.
    source_id:
        Reference to the original source document.
    section:
        Section or chapter within the source document.
    tags:
        Domain-specific tags for filtering and retrieval.
    metadata:
        Arbitrary key-value metadata (e.g., ``{"last_reviewed": "2025-01-01"}``).
    """

    entry_id: str
    title: str
    content: str
    source_id: str = ""
    section: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class KnowledgeBase(ABC):
    """Abstract base class for domain knowledge storage and retrieval."""

    @abstractmethod
    def add(self, entry: KnowledgeEntry) -> None:
        """Add an entry to the knowledge base.

        Parameters
        ----------
        entry:
            The :class:`KnowledgeEntry` to store.
        """

    @abstractmethod
    def get(self, entry_id: str) -> KnowledgeEntry | None:
        """Retrieve an entry by its unique identifier.

        Parameters
        ----------
        entry_id:
            The unique key of the entry to fetch.

        Returns
        -------
        KnowledgeEntry | None
            The entry, or ``None`` if not found.
        """

    @abstractmethod
    def search(self, query: str, tags: list[str] | None = None) -> list[KnowledgeEntry]:
        """Return entries whose content or title matches the query.

        Parameters
        ----------
        query:
            A free-text search string.
        tags:
            Optional list of tag filters; only entries with at least one
            matching tag are returned.

        Returns
        -------
        list[KnowledgeEntry]
            Matching entries, ordered by relevance (implementation-defined).
        """

    @abstractmethod
    def remove(self, entry_id: str) -> bool:
        """Remove an entry by its unique identifier.

        Parameters
        ----------
        entry_id:
            The unique key of the entry to remove.

        Returns
        -------
        bool
            ``True`` if the entry existed and was removed; ``False`` otherwise.
        """

    @abstractmethod
    def all_entries(self) -> list[KnowledgeEntry]:
        """Return all entries in the knowledge base."""


class InMemoryKB(KnowledgeBase):
    """In-memory knowledge base backed by a plain Python dictionary.

    Suitable for unit tests, small domain-specific lookups, and prototyping.
    For production workloads with large corpora, replace with a vector-store
    or full-text-search implementation.

    Example
    -------
    ::

        kb = InMemoryKB()
        kb.add(KnowledgeEntry(
            entry_id="hipaa-phi-001",
            title="HIPAA PHI Definition",
            content="Protected Health Information (PHI) is any information...",
            source_id="hipaa-privacy-rule",
            tags=["hipaa", "phi"],
        ))
        results = kb.search("protected health information", tags=["hipaa"])
    """

    def __init__(self) -> None:
        self._store: dict[str, KnowledgeEntry] = {}

    def add(self, entry: KnowledgeEntry) -> None:
        self._store[entry.entry_id] = entry

    def get(self, entry_id: str) -> KnowledgeEntry | None:
        return self._store.get(entry_id)

    def search(self, query: str, tags: list[str] | None = None) -> list[KnowledgeEntry]:
        """Simple case-insensitive substring search with optional tag filtering."""
        query_lower = query.lower()
        results: list[KnowledgeEntry] = []
        for entry in self._store.values():
            # Tag filtering
            if tags and not any(tag in entry.tags for tag in tags):
                continue
            # Text matching on title and content
            if query_lower in entry.title.lower() or query_lower in entry.content.lower():
                results.append(entry)
        return results

    def remove(self, entry_id: str) -> bool:
        if entry_id in self._store:
            del self._store[entry_id]
            return True
        return False

    def all_entries(self) -> list[KnowledgeEntry]:
        return list(self._store.values())

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"InMemoryKB(entries={len(self._store)})"
