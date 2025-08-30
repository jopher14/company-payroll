#!/bin/bash
# linter.sh - run flake8 and mypy with colored output

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "======================"
echo "Running flake8 (linting)..."
echo "======================"

# Run flake8 and capture exit code
flake8 .
flake8_exit=$?

if [ $flake8_exit -ne 0 ]; then
    echo -e "${RED}❌ flake8 found issues.${NC}"
else
    echo -e "${GREEN}✔ flake8 passed!${NC}"
fi

echo
echo "======================"
echo "Running mypy (type checking)..."
echo "======================"

# Run mypy and capture exit code
mypy .
mypy_exit=$?

if [ $mypy_exit -ne 0 ]; then
    echo -e "${RED}❌ mypy found issues.${NC}"
else
    echo -e "${GREEN}✔ mypy passed!${NC}"
fi

echo
echo -e "${GREEN}✅ Linting and type checking completed!${NC}"

# Exit with combined exit code (0 if both pass, 1 if any fail)
if [ $flake8_exit -ne 0 ] || [ $mypy_exit -ne 0 ]; then
    exit 1
else
    exit 0
fi
