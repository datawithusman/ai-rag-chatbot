"""Vector store service — manages ChromaDB operations for document embeddings."""

import logging
import shutil
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_core.documents import Document as LCDocument

from app.core.config import get_settings
from app.core.exceptions import DocumentNotFoundError

logger = logging.getLogger(__name__)
settings = get_settings()


class VectorStoreService:
    """Manages vector storage and similarity search using ChromaDB."""

    def __init__(self) -> None:
        self._persist_dir = Path(settings.chroma_persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Vector store initialized with %d existing documents",
            self._collection.count(),
        )

    def add_documents(
        self,
        chunks: list[LCDocument],
        document_id: str,
    ) -> int:
        """Add document chunks to the vector store.

        Args:
            chunks: List of LangChain document chunks.
            document_id: The parent document ID.

        Returns:
            Number of chunks added.
        """
        if not chunks:
            logger.warning("No chunks to add for document %s", document_id)
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk.page_content)
            metadata = {
                k: str(v) for k, v in chunk.metadata.items()
            }
            metadatas.append(metadata)

        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        logger.info(
            "Added %d chunks for document %s",
            len(chunks),
            document_id,
        )
        return len(chunks)

    def similarity_search(
        self,
        query: str,
        n_results: int = 5,
        document_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform similarity search against the vector store.

        Args:
            query: The search query.
            n_results: Number of results to return.
            document_ids: Optional filter to restrict search scope.

        Returns:
            List of search results with content, metadata, and distance.
        """
        where_filter: dict[str, Any] | None = None
        if document_ids:
            where_filter = {
                "document_id": {"$in": document_ids}
            }

        results = self._collection.query(
            query_texts=[query],
            n_results=min(n_results, self._collection.count() or 1),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        if not results["documents"] or not results["documents"][0]:
            return []

        search_results: list[dict[str, Any]] = []
        for i, doc in enumerate(results["documents"][0]):
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0.0

            search_results.append(
                {
                    "content": doc,
                    "metadata": metadata,
                    "relevance_score": round(1.0 - distance, 4),
                    "document_name": metadata.get("document_name", "Unknown"),
                    "page_number": metadata.get("page", None),
                }
            )

        return search_results

    def delete_document(self, document_id: str) -> int:
        """Delete all chunks for a given document.

        Args:
            document_id: The document ID to remove.

        Returns:
            Number of chunks deleted.

        Raises:
            DocumentNotFoundError: If no chunks found for the document.
        """
        results = self._collection.get(
            where={"document_id": document_id},
        )

        if not results["ids"]:
            raise DocumentNotFoundError(document_id)

        self._collection.delete(ids=results["ids"])

        logger.info(
            "Deleted %d chunks for document %s",
            len(results["ids"]),
            document_id,
        )
        return len(results["ids"])

    @property
    def total_chunks(self) -> int:
        """Return the total number of chunks in the store."""
        return self._collection.count()

    def reset(self) -> None:
        """Reset the entire vector store (useful for testing)."""
        self._client.delete_collection(settings.chroma_collection_name)
        self._collection = self._client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        logger.warning("Vector store has been reset")