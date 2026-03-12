"""API endpoint tests for the RAG system."""

from unittest.mock import MagicMock
import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# GET / — health / root
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    async def test_root_returns_ok(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------

class TestQueryEndpoint:
    async def test_query_with_new_session(self, client: AsyncClient, mock_rag_system: MagicMock):
        """When no session_id is provided, the server should create one."""
        resp = await client.post("/api/query", json={"query": "What is Python?"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "Python is a programming language."
        assert body["sources"] == ["Course: Intro to Python – Lesson 1"]
        assert body["session_id"] == "session_1"

        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("What is Python?", "session_1")

    async def test_query_with_existing_session(self, client: AsyncClient, mock_rag_system: MagicMock):
        """When a session_id is provided, it should be forwarded as-is."""
        resp = await client.post(
            "/api/query",
            json={"query": "Tell me more", "session_id": "existing_42"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "existing_42"

        mock_rag_system.session_manager.create_session.assert_not_called()
        mock_rag_system.query.assert_called_once_with("Tell me more", "existing_42")

    async def test_query_missing_query_field(self, client: AsyncClient):
        """Omitting the required `query` field should return 422."""
        resp = await client.post("/api/query", json={})
        assert resp.status_code == 422

    async def test_query_empty_string(self, client: AsyncClient, mock_rag_system: MagicMock):
        """An empty query string is still valid per the schema."""
        mock_rag_system.query.return_value = ("", [])

        resp = await client.post("/api/query", json={"query": ""})
        assert resp.status_code == 200
        assert resp.json()["answer"] == ""

    async def test_query_rag_system_error(self, client: AsyncClient, mock_rag_system: MagicMock):
        """Internal RAG failures should surface as 500."""
        mock_rag_system.query.side_effect = RuntimeError("vector store unavailable")

        resp = await client.post("/api/query", json={"query": "anything"})
        assert resp.status_code == 500
        assert "vector store unavailable" in resp.json()["detail"]

    async def test_query_returns_multiple_sources(self, client: AsyncClient, mock_rag_system: MagicMock):
        mock_rag_system.query.return_value = (
            "Here are the details.",
            ["Source A", "Source B", "Source C"],
        )

        resp = await client.post("/api/query", json={"query": "details"})
        assert resp.status_code == 200
        assert len(resp.json()["sources"]) == 3


# ---------------------------------------------------------------------------
# GET /api/courses
# ---------------------------------------------------------------------------

class TestCoursesEndpoint:
    async def test_get_courses(self, client: AsyncClient, mock_rag_system: MagicMock):
        resp = await client.get("/api/courses")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_courses"] == 2
        assert "Intro to Python" in body["course_titles"]
        assert "Advanced ML" in body["course_titles"]

        mock_rag_system.get_course_analytics.assert_called_once()

    async def test_get_courses_empty(self, client: AsyncClient, mock_rag_system: MagicMock):
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = await client.get("/api/courses")
        assert resp.status_code == 200
        assert resp.json()["total_courses"] == 0
        assert resp.json()["course_titles"] == []

    async def test_get_courses_error(self, client: AsyncClient, mock_rag_system: MagicMock):
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("db down")

        resp = await client.get("/api/courses")
        assert resp.status_code == 500
        assert "db down" in resp.json()["detail"]
