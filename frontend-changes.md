# Testing Infrastructure Changes

## Summary
Enhanced the RAG system with API testing infrastructure. No frontend files were modified — all changes are backend testing additions.

## Files Added

### `backend/tests/__init__.py`
- Empty package init to make tests a proper Python package.

### `backend/tests/conftest.py`
- Shared pytest fixtures for all API tests.
- `mock_rag_system` — pre-configured `MagicMock` with default return values for `query()`, `get_course_analytics()`, and `session_manager.create_session()`.
- `test_app` — lightweight FastAPI app that mirrors the real endpoints (`/api/query`, `/api/courses`, `/`) but avoids the static file mount that causes import errors in tests.
- `client` — async `httpx.AsyncClient` wired to the test app via `ASGITransport`.

### `backend/tests/test_api.py`
- **10 tests** across three endpoint groups:
  - `TestRootEndpoint` (1 test) — verifies `GET /` returns status ok.
  - `TestQueryEndpoint` (6 tests) — covers new session creation, existing session forwarding, missing query field (422), empty query, RAG error (500), and multiple sources.
  - `TestCoursesEndpoint` (3 tests) — covers normal response, empty catalog, and error propagation.

## Files Modified

### `pyproject.toml`
- Added `[dependency-groups] test` with `pytest>=8.0`, `pytest-asyncio>=0.25`, `httpx>=0.28`.
- Added `[tool.pytest.ini_options]` with `testpaths`, `asyncio_mode = "auto"`, and warning filters.
