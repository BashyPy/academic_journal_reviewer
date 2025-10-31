import pytest

from app.services.domain_detector import DomainDetector


@pytest.fixture
def domain_detector():
    return DomainDetector()


def test_detect_medical_domain(domain_detector):
    text = "This study examines patient outcomes in clinical trials"
    domain = domain_detector.detect_domain(text)
    assert "Medical" in domain or "Biomedical" in domain


def test_detect_computer_science_domain(domain_detector):
    text = "We propose a new machine learning algorithm for data processing"
    domain = domain_detector.detect_domain(text)
    assert "Computer Science" in domain or "Engineering" in domain
