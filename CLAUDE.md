# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot for querying course materials. FastAPI backend serves both the API and a static HTML/JS/CSS frontend. Uses ChromaDB for vector storage, sentence-transformers for embeddings, and Anthropic Claude for response generation with tool-based search.

## Commands

```bash
# Install dependencies
uv sync

# Run the app (starts uvicorn on port 8000)
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

No test suite exists yet.

## Architecture

The backend uses a **tool-calling RAG pattern**: the AI model decides when to search course content via Anthropic's tool use API, rather than always retrieving context.

**Request flow:** `POST /api/query` → `RAGSystem.query()` → `AIGenerator` (Claude) → Claude may call `search_course_content` tool → `VectorStore.search()` → Claude synthesizes final answer.

### Key Components (`backend/`)

- **`app.py`** — FastAPI app, two endpoints: `POST /api/query` (chat), `GET /api/courses` (catalog stats). Mounts `frontend/` as static files at root. Loads docs from `../docs/` on startup.
- **`rag_system.py`** — Orchestrator. Wires together all components. Manages the query pipeline and document ingestion.
- **`ai_generator.py`** — Anthropic Claude client. Handles tool execution loop (initial response → tool call → tool result → final response). System prompt is a class constant.
- **`search_tools.py`** — Tool abstraction layer. `Tool` ABC defines the interface. `CourseSearchTool` wraps VectorStore search. `ToolManager` handles registration/execution/source tracking.
- **`vector_store.py`** — ChromaDB wrapper with two collections: `course_catalog` (title/metadata for course resolution) and `course_content` (chunked content). `search()` resolves fuzzy course names via catalog before searching content.
- **`document_processor.py`** — Parses course documents with a specific format (header lines: `Course Title:`, `Course Link:`, `Course Instructor:`, then `Lesson N:` markers). Chunks text by sentences with configurable overlap.
- **`session_manager.py`** — In-memory conversation history per session. History is formatted as text and injected into the system prompt.
- **`config.py`** — Dataclass config loaded from `.env`. Key settings: `CHUNK_SIZE=800`, `CHUNK_OVERLAP=100`, `MAX_RESULTS=5`, embedding model `all-MiniLM-L6-v2`.
- **`models.py`** — Pydantic models: `Course`, `Lesson`, `CourseChunk`.

### Frontend (`frontend/`)

Plain HTML/JS/CSS — no build step. `index.html`, `script.js`, `style.css`. Served by FastAPI's StaticFiles mount.

### Data (`docs/`)

Course transcript files (`course1_script.txt`, etc.) auto-loaded on startup. Expected format has metadata header lines followed by `Lesson N: Title` markers.

## Environment

- Python 3.13+, managed with `uv`
- Requires `ANTHROPIC_API_KEY` in `.env` file at project root
- ChromaDB persists to `backend/chroma_db/`
