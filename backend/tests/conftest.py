"""Shared test fixtures for RAG system API tests."""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient, ASGITransport
from pydantic import BaseModel
from typing import List, Optional


# ---------------------------------------------------------------------------
# Pydantic models (duplicated from app.py to avoid importing the real app,
# which mounts static files that don't exist in the test environment)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    session_id: str


class CourseStats(BaseModel):
    total_courses: int
    course_titles: List[str]


# ---------------------------------------------------------------------------
# Test FastAPI application (no static‑file mount, no startup event)
# ---------------------------------------------------------------------------

def _create_test_app(rag_system: MagicMock) -> FastAPI:
    """Build a lightweight FastAPI app wired to the given mock RAG system."""

    test_app = FastAPI(title="Test RAG API")

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @test_app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()
            answer, sources = rag_system.query(request.query, session_id)
            return QueryResponse(answer=answer, sources=sources, session_id=session_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @test_app.get("/")
    async def root():
        return {"status": "ok", "message": "Course Materials RAG System"}

    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_rag_system() -> MagicMock:
    """Pre-configured mock RAG system with sensible defaults."""
    rag = MagicMock()

    # Default session behaviour
    rag.session_manager.create_session.return_value = "session_1"

    # Default query behaviour
    rag.query.return_value = (
        "Python is a programming language.",
        ["Course: Intro to Python – Lesson 1"],
    )

    # Default course analytics
    rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Intro to Python", "Advanced ML"],
    }

    return rag


@pytest.fixture()
def test_app(mock_rag_system: MagicMock) -> FastAPI:
    """FastAPI test application wired to mock_rag_system."""
    return _create_test_app(mock_rag_system)


@pytest.fixture()
async def client(test_app: FastAPI) -> AsyncClient:
    """Async HTTP client for the test app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
