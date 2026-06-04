"""LLM service — manages language model interactions and prompt engineering."""

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.exceptions import LLMConfigurationError
from app.models.schemas import ChatResponse, SourceReference

logger = logging.getLogger(__name__)
settings = get_settings()

RAG_SYSTEM_PROMPT = """You are an intelligent AI assistant specialized in answering questions \
based on the provided document context. Follow these rules strictly:

1. **Answer ONLY from the provided context** — do not use external knowledge.
2. **Cite your sources** — reference the document name and page number when possible.
3. **Be concise but thorough** — provide complete answers without unnecessary filler.
4. **Acknowledge limitations** — if the context doesn't contain enough information, say so honestly.
5. **Use markdown formatting** — structure your response with headers, bullet points, and code blocks when appropriate.

Context from uploaded documents:
{context}

Previous conversation:
{conversation_history}
"""


class LLMService:
    """Service for managing LLM interactions with RAG pipeline."""

    def __init__(self) -> None:
        self._llm: BaseChatModel | None = None
        self._initialize_llm()

    def _initialize_llm(self) -> None:
        """Initialize the language model based on configuration."""
        try:
            if settings.llm_provider == "openai":
                if not settings.openai_api_key:
                    raise LLMConfigurationError("openai")
                self._llm = ChatOpenAI(
                    model=settings.model_name,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                    api_key=settings.openai_api_key,
                )
            else:
                raise LLMConfigurationError(settings.llm_provider)

            logger.info(
                "LLM initialized: provider=%s, model=%s",
                settings.llm_provider,
                settings.model_name,
            )
        except LLMConfigurationError:
            logger.warning("LLM not configured — running in demo mode")
            self._llm = None

    def generate_response(
        self,
        question: str,
        search_results: list[dict[str, Any]],
        conversation_history: str = "",
    ) -> ChatResponse:
        """Generate an AI response using retrieved context.

        Args:
            question: The user's question.
            search_results: Retrieved document chunks from vector store.
            conversation_history: Previous conversation for context.

        Returns:
            ChatResponse with answer and source references.
        """
        context = self._format_context(search_results)
        sources = self._extract_sources(search_results)

        if self._llm is None:
            return self._demo_response(question, context, sources)

        system_prompt = RAG_SYSTEM_PROMPT.format(
            context=context,
            conversation_history=conversation_history or "No previous messages.",
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]

        response = self._llm.invoke(messages)

        return ChatResponse(
            answer=response.content,
            sources=sources,
            conversation_id="",
            tokens_used=getattr(response, "usage_metadata", {}).get(
                "total_tokens", 0
            ),
        )

    def _format_context(self, results: list[dict[str, Any]]) -> str:
        """Format search results into a structured context string."""
        if not results:
            return "No relevant documents found."

        context_parts: list[str] = []
        for i, result in enumerate(results, 1):
            doc_name = result.get("document_name", "Unknown")
            page = result.get("page_number", "N/A")
            content = result.get("content", "")
            context_parts.append(
                f"--- Source {i}: {doc_name} (Page {page}) ---\n{content}\n"
            )

        return "\n".join(context_parts)

    def _extract_sources(
        self, results: list[dict[str, Any]]
    ) -> list[SourceReference]:
        """Extract source references from search results."""
        sources: list[SourceReference] = []
        seen: set[str] = set()

        for result in results:
            doc_name = result.get("document_name", "Unknown")
            if doc_name in seen:
                continue
            seen.add(doc_name)

            sources.append(
                SourceReference(
                    content=result.get("content", "")[:200] + "...",
                    page_number=result.get("page_number"),
                    document_name=doc_name,
                    relevance_score=result.get("relevance_score", 0.0),
                )
            )

        return sources

    def _demo_response(
        self,
        question: str,
        context: str,
        sources: list[SourceReference],
    ) -> ChatResponse:
        """Return a demo response when LLM is not configured."""
        return ChatResponse(
            answer=(
                f"**Demo Mode** — LLM is not configured.\n\n"
                f"Your question: *{question}*\n\n"
                f"Retrieved context:\n{context}\n\n"
                f"Configure your API key in `.env` to enable AI responses."
            ),
            sources=sources,
            conversation_id="",
            tokens_used=0,
        )

    @property
    def is_configured(self) -> bool:
        """Check if the LLM is properly configured."""
        return self._llm is not None