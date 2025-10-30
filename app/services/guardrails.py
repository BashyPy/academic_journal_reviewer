import re
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class GuardrailViolation:
    type: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    action: str  # "warn", "block", "sanitize"


class AcademicGuardrails:
    def __init__(self):
        self.ethical_keywords = [
            "plagiarism",
            "fabrication",
            "falsification",
            "misconduct",
            "duplicate",
            "self-plagiarism",
            "ghost author",
            "gift author",
        ]

        self.sensitive_patterns = [
            r"\b(?:patient|participant|subject)\s+(?:name|id|identifier)\b",
            r"\b(?:email|phone|address|ssn|social security)\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ]

    def validate_submission(
        self, submission: Dict[str, Any]
    ) -> List[GuardrailViolation]:
        violations = []

        # Check content appropriateness
        violations.extend(self._check_content_ethics(submission))
        violations.extend(self._check_sensitive_data(submission))
        violations.extend(self._check_submission_integrity(submission))

        return violations

    def validate_review_output(self, review: str) -> List[GuardrailViolation]:
        violations = []

        # Check review professionalism
        violations.extend(self._check_review_tone(review))
        violations.extend(self._check_bias_indicators(review))

        return violations

    def _check_content_ethics(
        self, submission: Dict[str, Any]
    ) -> List[GuardrailViolation]:
        violations = []
        content = submission.get("content", "").lower()

        for keyword in self.ethical_keywords:
            if keyword in content:
                violations.append(
                    GuardrailViolation(
                        type="ethical_concern",
                        severity="high",
                        message=f"Potential ethical issue detected: {keyword}",
                        action="warn",
                    )
                )

        return violations

    def _check_sensitive_data(
        self, submission: Dict[str, Any]
    ) -> List[GuardrailViolation]:
        violations = []
        content = submission.get("content", "")

        for pattern in self.sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        type="sensitive_data",
                        severity="critical",
                        message="Potential sensitive/personal data detected",
                        action="block",
                    )
                )

        return violations

    def _check_submission_integrity(
        self, submission: Dict[str, Any]
    ) -> List[GuardrailViolation]:
        violations = []

        # Check minimum content requirements
        content = submission.get("content", "")
        if len(content.strip()) < 100:
            violations.append(
                GuardrailViolation(
                    type="content_quality",
                    severity="medium",
                    message="Submission too short for meaningful review",
                    action="warn",
                )
            )

        return violations

    def _check_review_tone(self, review: str) -> List[GuardrailViolation]:
        violations = []

        # Check for unprofessional language
        unprofessional_terms = ["terrible", "awful", "stupid", "ridiculous", "garbage"]
        review_lower = review.lower()

        for term in unprofessional_terms:
            if term in review_lower:
                violations.append(
                    GuardrailViolation(
                        type="unprofessional_tone",
                        severity="medium",
                        message=f"Unprofessional language detected: {term}",
                        action="sanitize",
                    )
                )

        return violations

    def _check_bias_indicators(self, review: str) -> List[GuardrailViolation]:
        violations = []

        # Check for potential bias indicators
        bias_patterns = [
            r"\b(?:obviously|clearly|any fool)\b",
            r"\b(?:always|never|all|none)\s+(?:researchers|studies|papers)\b",
        ]

        for pattern in bias_patterns:
            if re.search(pattern, review, re.IGNORECASE):
                violations.append(
                    GuardrailViolation(
                        type="potential_bias",
                        severity="low",
                        message="Potential bias language detected",
                        action="warn",
                    )
                )

        return violations

    def sanitize_content(
        self, content: str, violations: List[GuardrailViolation]
    ) -> str:
        sanitized = content

        for violation in violations:
            if (
                violation.action == "sanitize"
                and violation.type == "unprofessional_tone"
            ):
                # Replace unprofessional terms with neutral alternatives
                replacements = {
                    "terrible": "inadequate",
                    "awful": "problematic",
                    "stupid": "unclear",
                    "ridiculous": "questionable",
                    "garbage": "insufficient",
                }

                for bad_term, good_term in replacements.items():
                    sanitized = re.sub(
                        bad_term, good_term, sanitized, flags=re.IGNORECASE
                    )

        return sanitized


# Global instance
guardrails = AcademicGuardrails()
