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
