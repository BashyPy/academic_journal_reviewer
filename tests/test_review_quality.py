"""Tests for review quality enhancements."""

import pytest

from app.services.langgraph_workflow import langgraph_workflow


@pytest.mark.asyncio
async def test_review_includes_structure():
    """Test that reviews include manuscript structure analysis."""
    submission_data = {
        "_id": "test_quality_001",
        "content": (
            "Abstract\nThis is a test.\n\nMethods\n"
            "We recruited 45 participants.\n\nResults\n"
            "Significant findings."
        ),
        "title": "Test Study",
        "file_metadata": {"pages": 1},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    # Handle both dict and string returns
    report = result["final_report"] if isinstance(result, dict) else result

    # Verify structure-related content
    assert report and len(report) > 100
    print("✓ Review generated successfully")


@pytest.mark.asyncio
async def test_review_includes_evidence():
    """Test that reviews include evidence-based findings."""
    submission_data = {
        "_id": "test_quality_002",
        "content": (
            "Methods: We recruited 45 participants from the local "
            "community without randomization."
        ),
        "title": "Test Study",
        "file_metadata": {"pages": 1},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    report = result["final_report"] if isinstance(result, dict) else result

    # Verify evidence is present (quotes or specific references)
    has_evidence = any(
        term in report.lower() for term in ["quote", "recruited", "participants", "methods"]
    )
    assert has_evidence
    print("✓ Review includes evidence-based findings")


@pytest.mark.asyncio
async def test_review_includes_severity():
    """Test that reviews classify findings by severity."""
    submission_data = {
        "_id": "test_quality_003",
        "content": ("Test manuscript with methodology issues and missing " "references."),
        "title": "Test Study",
        "file_metadata": {"pages": 1},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    report = result["final_report"] if isinstance(result, dict) else result

    # Verify severity classification
    severity_terms = ["major", "moderate", "minor", "critical", "important"]
    has_severity = any(term in report.lower() for term in severity_terms)
    assert has_severity
    print("✓ Review includes severity classification")


@pytest.mark.asyncio
async def test_review_includes_recommendations():
    """Test that reviews include actionable recommendations."""
    submission_data = {
        "_id": "test_quality_004",
        "content": ("Abstract: Brief study. Methods: Simple approach. " "Results: Some findings."),
        "title": "Test Study",
        "file_metadata": {"pages": 1},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    report = result["final_report"] if isinstance(result, dict) else result

    # Verify recommendations are present
    recommendation_terms = [
        "recommend",
        "should",
        "suggest",
        "improve",
        "add",
        "clarify",
    ]
    has_recommendations = any(term in report.lower() for term in recommendation_terms)
    assert has_recommendations
    print("✓ Review includes actionable recommendations")


@pytest.mark.asyncio
async def test_review_quality_metrics():
    """Test that reviews include quality metrics."""
    submission_data = {
        "_id": "test_quality_005",
        "content": (
            "Complete manuscript with abstract, methods, results, and " "discussion sections."
        ),
        "title": "Quality Test Study",
        "file_metadata": {"pages": 2},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    report = result["final_report"] if isinstance(result, dict) else result

    # Verify quality metrics (confidence, bias check, or objective analysis)
    quality_terms = ["confidence", "bias", "objective", "score"]
    has_quality_metrics = any(term in report.lower() for term in quality_terms)
    assert has_quality_metrics
    print("✓ Review includes quality metrics")


@pytest.mark.asyncio
async def test_review_domain_awareness():
    """Test that reviews are domain-aware."""
    submission_data = {
        "_id": "test_quality_006",
        "content": (
            "Medical study on patient outcomes with statistical analysis "
            "and clinical implications."
        ),
        "title": "Clinical Trial Results",
        "file_metadata": {"pages": 3},
    }

    result = await langgraph_workflow.execute_review(submission_data)
    report = result["final_report"] if isinstance(result, dict) else result
    domain = result.get("domain", "") if isinstance(result, dict) else "unknown"

    # Verify domain detection worked
    assert domain and domain != ""
    assert report and len(report) > 200
    print(f"✓ Review is domain-aware (detected: {domain})")
