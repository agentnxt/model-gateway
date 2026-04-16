#!/bin/bash
# scripts/build-test.sh
# Run this BEFORE pushing to verify all Dockerfiles build correctly.
# Usage: bash scripts/build-test.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }
info() { echo -e "${YELLOW}→ $1${NC}"; }

echo "================================================"
echo " Autonomyx Model Gateway — Pre-push Build Test"
echo "================================================"
echo ""

# 1. Validate docker-compose.yml syntax
info "Validating docker-compose.yml..."
docker compose config --quiet && pass "docker-compose.yml syntax OK" || fail "docker-compose.yml invalid"

# 2. Run unit tests
info "Running unit tests..."
if command -v pytest &> /dev/null; then
    pytest tests/ -q --tb=short && pass "All tests passed" || fail "Tests failed"
else
    pip install -q -r tests/requirements.txt
    pytest tests/ -q --tb=short && pass "All tests passed" || fail "Tests failed"
fi

# 3. Lint Dockerfiles with hadolint (if available)
if command -v hadolint &> /dev/null; then
    info "Linting Dockerfiles..."
    for df in playwright/Dockerfile classifier/Dockerfile translator/Dockerfile; do
        hadolint $df && pass "$df lint OK" || fail "$df lint failed"
    done
else
    info "hadolint not installed — skipping lint (install: brew install hadolint)"
fi

# 4. Build all images
IMAGES=(
    "playwright:./playwright"
    "classifier:./classifier"
    "translator:./translator"
)

for entry in "${IMAGES[@]}"; do
    name="${entry%%:*}"
    context="${entry##*:}"
    info "Building $name..."
    docker build \
        -t autonomyx-${name}:local-test \
        -f ${context}/Dockerfile \
        ${context} \
        --quiet && pass "$name image built OK" || fail "$name image build FAILED"
done

# 5. Cleanup test images
info "Cleaning up test images..."
docker rmi autonomyx-playwright:local-test \
           autonomyx-classifier:local-test \
           autonomyx-translator:local-test \
           --force 2>/dev/null || true

echo ""
echo "================================================"
echo -e " ${GREEN}All checks passed — safe to push${NC}"
echo "================================================"
