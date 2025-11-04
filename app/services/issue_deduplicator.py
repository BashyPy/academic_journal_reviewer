from difflib import SequenceMatcher
from typing import Any, Dict, List


class IssueDeduplicator:
    # canonical severities and aliases for consistent handling across methods
    SEVERITIES = ["major", "moderate", "minor"]
    SEVERITY_ALIASES = {"high": "major", "medium": "moderate", "low": "minor"}

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
        # If a non-empty default was provided, respect it; otherwise return
        # a safe string representation of obj, falling back to default on error.
        if default != "":
            return default
        try:
            return str(obj)
        except Exception:
            return default

    def _get_severity(self, obj) -> str:
        # Extract a raw severity value from dicts, objects, or strings, then normalize aliases.
        if isinstance(obj, dict):
            raw = obj.get("severity", "moderate")
        elif hasattr(obj, "severity"):
            raw = getattr(obj, "severity")
        elif isinstance(obj, str):
            raw = obj
        else:
            raw = "moderate"

        raw_str = str(raw).lower()
        # map common aliases (e.g., high/medium/low) to canonical severities
        return self.SEVERITY_ALIASES.get(raw_str, raw_str)

    def _merge_if_higher(self, existing, incoming) -> None:
        severity_order = {"major": 3, "moderate": 2, "minor": 1}
        try:
            incoming_score = severity_order.get(self._get_severity(incoming), 0)
            existing_score = severity_order.get(self._get_severity(existing), 0)
        except Exception:
            # If we cannot determine severities, avoid merging to prevent data loss
            return

        if incoming_score <= existing_score:
            return

        # perform a safe update depending on types, guarding against unexpected errors
        try:
            if isinstance(existing, dict):
                existing.update(
                    incoming if isinstance(incoming, dict) else getattr(incoming, "__dict__", {})
                )
            elif hasattr(existing, "__dict__"):
                existing.__dict__.update(
                    incoming if isinstance(incoming, dict) else getattr(incoming, "__dict__", {})
                )
        except Exception:
            # Swallow errors here to keep deduplication robust; nothing to merge on failure.
            return

    def _is_similar(self, text1: str, text2: str) -> bool:
        return self.calculate_similarity(text1, text2) > self.similarity_threshold

    def deduplicate_issues(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate issues based on description similarity."""
        unique_issues = []
        for issue in issues:
            description = issue.get("description", "")
            is_duplicate = False

            for existing in list(unique_issues):
                existing_desc = existing.get("description", "")
                if self._is_similar(description, existing_desc):
                    # Keep the one with higher severity
                    severity_order = {"high": 3, "medium": 2, "low": 1}
                    if severity_order.get(issue.get("severity", "low"), 1) > severity_order.get(
                        existing.get("severity", "low"), 1
                    ):
                        unique_issues.remove(existing)
                        unique_issues.append(issue)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_issues.append(issue)

        return unique_issues

    def deduplicate_findings(self, all_findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings across agents."""
        unique_findings: List[Dict[str, Any]] = []
        # Keep a parallel list of normalized finding texts to avoid repeated _get_field calls
        unique_texts: List[str] = []

        for finding in all_findings:
            raw_finding = self._get_field(finding, "finding", str(finding))
            finding_text = raw_finding.lower()
            matched = False

            # iterate with index to reuse the cached normalized texts
            for idx, existing in enumerate(unique_findings):
                existing_text = unique_texts[idx]
                if self._is_similar(finding_text, existing_text):
                    # merge if incoming has higher severity
                    self._merge_if_higher(existing, finding)
                    matched = True
                    break

            if not matched:
                unique_findings.append(finding)
                unique_texts.append(finding_text)

        return unique_findings

    def prioritize_issues(self, findings: List[Dict[str, Any]]) -> Dict[str, List]:
        """Group findings by priority/severity using canonical severity buckets."""
        prioritized: Dict[str, List[Any]] = {s: [] for s in self.SEVERITIES}

        for finding in findings:
            severity = self._get_severity(finding)
            if severity not in prioritized:
                # default to moderate for unknown severities
                severity = "moderate"
            prioritized[severity].append(finding)

        return prioritized


issue_deduplicator = IssueDeduplicator()
