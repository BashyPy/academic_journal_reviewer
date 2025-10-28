from difflib import SequenceMatcher
from typing import Any, Dict, List


class IssueDeduplicator:
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def deduplicate_findings(
        self, all_findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate findings across agents."""
        unique_findings = []

        for finding in all_findings:
            finding_text = (
                finding.get("finding", "")
                if hasattr(finding, "finding")
                else str(finding)
            )

            is_duplicate = False
            for existing in unique_findings:
                existing_text = (
                    existing.get("finding", "")
                    if hasattr(existing, "finding")
                    else str(existing)
                )

                if (
                    self.calculate_similarity(finding_text, existing_text)
                    > self.similarity_threshold
                ):
                    # Merge findings - keep higher severity
                    if hasattr(finding, "severity") and hasattr(existing, "severity"):
                        severity_order = {"major": 3, "moderate": 2, "minor": 1}
                        if severity_order.get(finding.severity, 0) > severity_order.get(
                            existing.severity, 0
                        ):
                            existing.update(
                                finding.__dict__
                                if hasattr(finding, "__dict__")
                                else finding
                            )
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_findings.append(finding)

        return unique_findings

    def prioritize_issues(self, findings: List[Dict[str, Any]]) -> Dict[str, List]:
        """Group findings by priority/severity."""
        prioritized = {"major": [], "moderate": [], "minor": []}

        for finding in findings:
            severity = (
                getattr(finding, "severity", "moderate")
                if hasattr(finding, "severity")
                else "moderate"
            )
            if severity in prioritized:
                prioritized[severity].append(finding)
            else:
                prioritized["moderate"].append(finding)

        return prioritized


issue_deduplicator = IssueDeduplicator()
