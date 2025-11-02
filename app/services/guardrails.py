import re
from dataclasses import dataclass
from typing import Any, Dict, List

from app.utils.logger import get_logger


@dataclass
class GuardrailViolation:
    type: str
    severity: str  # "low", "medium", "high", "critical"
    message: str
    action: str  # "warn", "block", "sanitize"

    VALID_SEVERITIES = ("low", "medium", "high", "critical")
    VALID_ACTIONS = ("warn", "block", "sanitize")

    def __post_init__(self):
        # Basic type and content validation with normalization
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("GuardrailViolation 'type' must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("GuardrailViolation 'message' must be a non-empty string.")

        if not isinstance(self.severity, str):
            raise ValueError("GuardrailViolation 'severity' must be a string.")
        self.severity = self.severity.strip().lower()
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(
                f"GuardrailViolation 'severity' must be one of {self.VALID_SEVERITIES}."
            )

        if not isinstance(self.action, str):
            raise ValueError("GuardrailViolation 'action' must be a string.")
        self.action = self.action.strip().lower()
        if self.action not in self.VALID_ACTIONS:
            raise ValueError(
                f"GuardrailViolation 'action' must be one of {self.VALID_ACTIONS}."
            )


class AcademicGuardrails:
    # Minimum required characters for a submission to be considered meaningful.
    MIN_CONTENT_LENGTH = 100

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

        # Precompile sensitive data regexes and handle any compilation errors.
        # Fix the email regex character class and compile with IGNORECASE.
        sensitive_pattern_strings = [
            r"\b(?:patient|participant|subject)\s+(?:name|id|identifier)\b",
            r"\b(?:email|phone|address|ssn|social security)\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        ]
        self.sensitive_patterns = []
        for p in sensitive_pattern_strings:
            try:
                self.sensitive_patterns.append(re.compile(p, re.IGNORECASE))
            except re.error:
                # Skip invalid patterns; in production consider logging the failure.
                continue

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

        # Safely obtain and normalize content to a lowercase string.
        raw_content = submission.get("content", "")
        try:
            if raw_content is None:
                content = ""
            elif isinstance(raw_content, str):
                content = raw_content.lower()
            else:
                # Attempt a best-effort coercion for non-string types
                content = str(raw_content).lower()
        except Exception:
            # Fail-safe: on any unexpected error treat as empty content
            content = ""

        for keyword in self.ethical_keywords:
            if keyword in content:
                violations.append(
                    GuardrailViolation(
                        type="ethical_concern",
                        severity="high",
                        message=f"Ethical keyword detected: {keyword}",
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
            try:
                # patterns are precompiled; use .search to avoid recompiling and to catch regex errors
                if hasattr(pattern, "search"):
                    match = pattern.search(content)
                else:
                    # fallback if an entry is still a string
                    match = re.search(pattern, content, re.IGNORECASE)
            except re.error:
                # If a regex operation fails, skip that pattern rather than crashing
                continue

            if match:
                violations.append(
                    GuardrailViolation(
                        type="sensitive_data",
                        severity="critical",
                        message="Potential sensitive/personal data detected",
                        action="block",
                    )
                )

    def _check_submission_integrity(
        self, submission: Dict[str, Any]
    ) -> List[GuardrailViolation]:
        violations = []

        # Check minimum content requirements
        raw_content = submission.get("content", "")
        try:
            if raw_content is None:
                content = ""
            elif isinstance(raw_content, str):
                content = raw_content
            else:
                # Best-effort coercion for non-string types
                content = str(raw_content)
        except Exception:
            # Fail-safe: treat as empty content on unexpected errors
            content = ""

        min_len = getattr(self, "MIN_CONTENT_LENGTH", 100)
        if len(content.strip()) < min_len:
            violations.append(
                GuardrailViolation(
                    type="content_quality",
                    severity="medium",
                    message=f"Submission too short for meaningful review (minimum {min_len} characters)",
                    action="warn",
                )
            )

        return violations

    def _check_review_tone(self, review: str) -> List[GuardrailViolation]:
        violations = []

        # Check for unprofessional language; handle missing or invalid input safely.
        unprofessional_terms = ["terrible", "awful", "stupid", "ridiculous", "garbage"]

        try:
            if review is None:
                review_normalized = ""
            elif isinstance(review, str):
                review_normalized = review.lower()
            else:
                # Best-effort coercion for non-string types
                review_normalized = str(review).lower()
        except Exception as exc:
            # Log the normalization error and proceed with an empty string to avoid crashing.
            get_logger(__name__).debug(
                f"Error normalizing review text: {exc}",
                {"component": "guardrails", "function": "_check_review_tone"},
            )
            review_normalized = ""

        for term in unprofessional_terms:
            if term in review_normalized:
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

        # Normalize input to a string to avoid TypeErrors and improve readability
        try:
            if review is None:
                review_text = ""
            elif isinstance(review, str):
                review_text = review
            else:
                review_text = str(review)
        except Exception:
            review_text = ""

        for pattern in bias_patterns:
            try:
                if re.search(pattern, review_text, re.IGNORECASE):
                    violations.append(
                        GuardrailViolation(
                            type="potential_bias",
                            severity="low",
                            message="Potential bias language detected",
                            action="warn",
                        )
                    )
            except re.error:
                # Skip invalid regex pattern rather than crashing
                continue

        return violations

    def filter_content(self, content: str) -> Dict[str, Any]:
        """Filter content and return safety assessment."""
        violations = self._check_sensitive_data({"content": content})
        violations.extend(self._check_content_ethics({"content": content}))

        high_severities = {"high", "critical"}
        has_high_severity = any(v.severity in high_severities for v in violations)

        return {
            "is_safe": not has_high_severity,
            "violations": violations,
            "content": content,
        }

    def detect_bias(self, text: str) -> Dict[str, Any]:
        """Detect potential bias in text."""
        violations = self._check_bias_indicators(text)

        # Weight per detected violation and clamp to [0.0, 1.0]
        per_violation_weight = 0.2
        bias_score = min(len(violations) * per_violation_weight, 1.0)

        # Threshold for considering text biased (tunable constant)
        bias_threshold = 0.3
        has_bias = bias_score > bias_threshold

        return {
            "bias_score": bias_score,
            "violations": violations,
            "has_bias": has_bias,
        }

    def sanitize_content(
        self, content: str, violations: List[GuardrailViolation]
    ) -> str:
        """
        Sanitize content by replacing unprofessional terms when a corresponding
        'sanitize' + 'unprofessional_tone' violation is present.
        """
        # Ensure sanitized is a string
        sanitized = content if isinstance(content, str) else str(content)

        # Determine whether any violation requires sanitization
        requires_sanitize = any(
            getattr(v, "action", "") == "sanitize"
            and getattr(v, "type", "") == "unprofessional_tone"
            for v in violations
        )
        if not requires_sanitize:
            return sanitized

        replacements = {
            "terrible": "inadequate",
            "awful": "problematic",
            "stupid": "unclear",
            "ridiculous": "questionable",
            "garbage": "insufficient",
        }

        # Compile a single regex that matches any bad term, case-insensitive,
        # and perform a single substitution pass using a replacement function.
        try:
            pattern = re.compile(
                "|".join(re.escape(k) for k in replacements.keys()), re.IGNORECASE
            )

            def _repl(match):
                return replacements.get(match.group(0).lower(), match.group(0))

            sanitized = pattern.sub(_repl, sanitized)
        except re.error as exc:
            get_logger(__name__).debug(
                f"Regex sanitization failed: {exc}",
                {"component": "guardrails", "function": "sanitize_content"},
            )
        except Exception as exc:
            get_logger(__name__).debug(
                f"Unexpected error during sanitize_content: {exc}",
                {"component": "guardrails", "function": "sanitize_content"},
            )

        return sanitized


# Global instance
guardrails = AcademicGuardrails()
