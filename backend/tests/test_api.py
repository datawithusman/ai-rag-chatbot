"""Tests for the API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root endpoint returns welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_chat_without_documents(client: AsyncClient):
    """Test chat endpoint returns error when no documents uploaded."""
    response = await client.post(
        "/api/v1/chat",
        json={"question": "What is AI?"},
    )
    assert response.status_code == 400
    assert "upload" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_with_empty_question(client: AsyncClient):
    """Test chat endpoint rejects empty questions."""
    response = await client.post(
        "/api/v1/chat",
        json={"question": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_with_long_question(client: AsyncClient):
    """Test chat endpoint rejects questions over 2000 chars."""
    response = await client.post(
        "/api/v1/chat",
        json={"question": "x" * 2001},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    """Test listing documents when none uploaded."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_delete_nonexistent_document(client: AsyncClient):
    """Test deleting a document that doesn't exist."""
    response = await client.delete("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404