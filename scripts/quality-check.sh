#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo "  Frontend Code Quality Checks"
echo "========================================="
echo ""

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    cd "$FRONTEND_DIR" && npm install
    echo ""
fi

cd "$FRONTEND_DIR"

# Track failures
FAILED=0

# 1. Prettier format check
echo "-----------------------------------------"
echo "  Prettier: Checking formatting..."
echo "-----------------------------------------"
if npx prettier --check '**/*.{html,css,js}' 2>/dev/null; then
    echo -e "${GREEN}Formatting: PASS${NC}"
else
    echo -e "${RED}Formatting: FAIL${NC}"
    echo "  Run 'npm run format' in frontend/ to fix"
    FAILED=1
fi
echo ""

# 2. ESLint
echo "-----------------------------------------"
echo "  ESLint: Checking JavaScript..."
echo "-----------------------------------------"
if npx eslint '**/*.js' 2>/dev/null; then
    echo -e "${GREEN}Linting: PASS${NC}"
else
    echo -e "${RED}Linting: FAIL${NC}"
    echo "  Run 'npm run lint:fix' in frontend/ to fix"
    FAILED=1
fi
echo ""

# Summary
echo "========================================="
if [ "$FAILED" -eq 0 ]; then
    echo -e "  ${GREEN}All quality checks passed!${NC}"
else
    echo -e "  ${RED}Some checks failed. See above for details.${NC}"
fi
echo "========================================="

exit $FAILED
