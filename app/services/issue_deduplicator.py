from difflib import SequenceMatcher
from typing import Any, Dict, List


class IssueDeduplicator:
    def __init__(self, similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _get_field(self, obj, field_name: str, default: Any = "") -> Any:
        if isinstance(obj, dict):
            return obj.get(field_name, default)
        if hasattr(obj, field_name):
            return getattr(obj, field_name)
        return default if default != "" else str(obj)

    def _get_severity(self, obj) -> str:
        if isinstance(obj, dict):
            return obj.get("severity", "moderate")
        if hasattr(obj, "severity"):
            return getattr(obj, "severity")
        return "moderate"

    def _merge_if_higher(self, existing, incoming) -> None:
        severity_order = {"major": 3, "moderate": 2, "minor": 1}
        if severity_order.get(self._get_severity(incoming), 0) <= severity_order.get(
            self._get_severity(existing), 0
        ):
            return
        # perform a safe update depending on types
        if isinstance(existing, dict):
            existing.update(
                incoming
                if isinstance(incoming, dict)
                else getattr(incoming, "__dict__", {})
            )
        elif hasattr(existing, "__dict__"):
            existing.__dict__.update(
                incoming
                if isinstance(incoming, dict)
                else getattr(incoming, "__dict__", {})
            )

    def _is_similar(self, text1: str, text2: str) -> bool:
        return self.calculate_similarity(text1, text2) > self.similarity_threshold

    def deduplicate_findings(
        self, all_findings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate findings across agents."""
        unique_findings: List[Dict[str, Any]] = []
        for finding in all_findings:
            finding_text = self._get_field(finding, "finding", str(finding))
            matched = False
            for existing in unique_findings:
                existing_text = self._get_field(existing, "finding", str(existing))
                if not self._is_similar(finding_text, existing_text):
                    continue
                # Similar enough -> merge if incoming has higher severity
                self._merge_if_higher(existing, finding)
                matched = True
                break
            if not matched:
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
