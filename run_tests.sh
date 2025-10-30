#!/bin/bash

echo "🧪 Running Comprehensive Test Suite for AARIS"
echo "=============================================="

# Backend Tests
echo "📊 Running Backend Tests with Coverage..."
cd "$(dirname "$0")"

# Install test dependencies
pip install -r requirements-test.txt

# Run backend tests with coverage
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing --cov-fail-under=80 -v

BACKEND_EXIT_CODE=$?

# Frontend Tests
echo ""
echo "🎨 Running Frontend Tests with Coverage..."
cd frontend

# Install frontend dependencies
npm install

# Run frontend tests with coverage
npm run test:coverage

FRONTEND_EXIT_CODE=$?

# Summary
echo ""
echo "📋 Test Summary"
echo "==============="

if [ $BACKEND_EXIT_CODE -eq 0 ]; then
    echo "✅ Backend Tests: PASSED (80%+ coverage)"
else
    echo "❌ Backend Tests: FAILED"
fi

if [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo "✅ Frontend Tests: PASSED (80%+ coverage)"
else
    echo "❌ Frontend Tests: FAILED"
fi

# Overall result
if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🎉 All tests passed with 80%+ coverage!"
    exit 0
else
    echo ""
    echo "💥 Some tests failed or coverage below 80%"
    exit 1
fi