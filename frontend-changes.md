# Frontend Code Quality Tools

## Changes Made

### New Files

- **`frontend/package.json`** — Node.js project config with dev dependencies and quality scripts
- **`frontend/.prettierrc`** — Prettier configuration (single quotes, trailing commas, 100 char width)
- **`frontend/eslint.config.js`** — ESLint flat config with recommended rules + custom rules (no-var, prefer-const, eqeqeq, curly braces required)
- **`scripts/quality-check.sh`** — Shell script that runs all frontend quality checks (format + lint)

### Modified Files

- **`frontend/script.js`** — Applied Prettier formatting and fixed ESLint errors:
  - Added curly braces to all `if` statements (enforced by `curly` rule)
  - Replaced `console.log` calls with comments (enforced by `no-console` rule)
  - Applied consistent formatting (single quotes, trailing commas, semicolons)
- **`frontend/index.html`** — Applied Prettier formatting for consistent indentation
- **`frontend/style.css`** — Applied Prettier formatting for consistent indentation
- **`.gitignore`** — Added `node_modules/` entry for frontend tooling

## Tools Installed

| Tool | Version | Purpose |
|------|---------|---------|
| Prettier | ^3.4.2 | Code formatting (HTML, CSS, JS) |
| ESLint | ^9.18.0 | JavaScript linting |
| @eslint/js | ^9.18.0 | ESLint recommended config |
| globals | ^15.14.0 | Browser globals for ESLint |

## Available Scripts

Run from `frontend/` directory:

| Command | Description |
|---------|-------------|
| `npm run format` | Auto-format all frontend files |
| `npm run format:check` | Check formatting without modifying files |
| `npm run lint` | Run ESLint on JavaScript files |
| `npm run lint:fix` | Auto-fix ESLint issues |
| `npm run quality` | Run all checks (format + lint) |
| `npm run quality:fix` | Auto-fix all issues |

Or from project root:

```bash
./scripts/quality-check.sh
```

---

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

---

# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a toggle button that allows users to switch between dark and light themes with smooth transitions and localStorage persistence.

## Files Modified

### 1. `frontend/index.html`
- Added a theme toggle button with sun/moon SVG icons inside `.container`, before `.main-content`
- Button includes `aria-label` and `title` for accessibility
- Uses `id="themeToggle"` for JS binding

### 2. `frontend/style.css`
- Added `[data-theme="light"]` CSS variable overrides for all theme colors:
  - Light background (`#f8fafc`), white surface (`#ffffff`)
  - Dark text (`#0f172a`) for contrast, muted secondary text (`#64748b`)
  - Adjusted borders (`#e2e8f0`), shadows, and code block backgrounds
- Added `.theme-toggle` styles: fixed position top-right, circular button, hover/focus/active states
- Added icon visibility rules: sun icon shows in dark mode, moon icon in light mode
- Added `transition` rules on key elements for smooth 0.3s theme switching

### 3. `frontend/script.js`
- Added `themeToggle` DOM element reference
- Added `initTheme()`: reads saved theme from `localStorage`, defaults to dark, applies `data-theme` attribute on `<html>`
- Added `toggleTheme()`: switches between dark/light, saves preference to `localStorage`
- Added `updateThemeToggleLabel()`: updates `aria-label` and `title` for screen readers
- Registered click listener on theme toggle button in `setupEventListeners()`

## Design Decisions
- Theme is applied via `data-theme` attribute on `<html>` element
- All existing CSS variables are overridden in light theme, so every element adapts automatically
- localStorage persistence means the user's preference survives page reloads
- Default theme is dark (matching the existing design)
- Button is `position: fixed` with `z-index: 100` to stay visible at all times
- Inline `<script>` in `<head>` applies saved theme before first paint to prevent flash of wrong theme

## Security & Accessibility Fixes (post-review)
- Escaped HTML in `sources` array and course titles before `innerHTML` injection (XSS prevention)
- Added `aria-hidden="true"` and `focusable="false"` to SVG icons to prevent screen reader noise
- Fixed `var(--primary)` to `var(--primary-color)` in blockquote border-left
- Moved error/success message colors to CSS variables with light-theme-appropriate contrast values
