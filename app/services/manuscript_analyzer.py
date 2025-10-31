import logging
import re
from typing import Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger(__name__)


class ManuscriptAnalyzer:
    def __init__(self):
        self.section_patterns = {
            "abstract": r"(?i)\b(abstract|summary)\b",
            "introduction": r"(?i)\b(introduction|background)\b",
            "methods": r"(?i)\b(methods?|methodology|materials?\s+and\s+methods?)\b",
            "results": r"(?i)\b(results?|findings?)\b",
            "discussion": r"(?i)\b(discussion|conclusion)\b",
            "references": r"(?i)\b(references?|bibliography)\b",
        }
        # Precompile patterns and skip any invalid ones to avoid per-line try/except
        self.compiled_section_patterns: List[Tuple[str, Pattern]] = []
        for name, pattern in self.section_patterns.items():
            try:
                compiled = re.compile(pattern)
                self.compiled_section_patterns.append((name, compiled))
            except re.error as e:
                logger.warning(
                    "Invalid regex pattern in section_patterns: %s (%s)", pattern, e
                )

    def _detect_section_header(self, stripped: str) -> Optional[str]:
        """Return the section name if the stripped line matches a header, otherwise None."""
        if not stripped or len(stripped) >= 100:
            return None
        for section_name, compiled in self.compiled_section_patterns:
            if compiled.search(stripped):
                return section_name
        return None

    def _ensure_section(
        self, sections: Dict[str, Dict], section_name: str, line_num: int
    ) -> None:
        """Ensure a section entry exists in sections with initial metadata."""
        if section_name not in sections:
            sections[section_name] = {
                "start_line": line_num,
                "content": [],
                "word_count": 0,
            }

    def analyze_structure(self, content: str) -> Dict[str, Dict]:
        """Analyze manuscript structure and identify sections."""
        lines = content.split("\n")
        sections: Dict[str, Dict] = {}
        current_section = "unknown"

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            # Detect and switch to a new section if this line is a header
            detected = self._detect_section_header(stripped)
            if detected:
                current_section = detected
                self._ensure_section(sections, current_section, line_num)

            # Ensure the current section exists and add the line
            if current_section not in sections:
                self._ensure_section(sections, current_section, line_num)

            sections[current_section]["content"].append((line_num, stripped))
            sections[current_section]["word_count"] += len(stripped.split())

        return sections

    def find_line_number(self, content: str, text: str) -> Optional[int]:
        """Find line number for specific text."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if text.lower() in line.lower():
                return i + 1
        return None

    def get_section_for_line(self, sections: Dict, line_num: int) -> str:
        """Determine which section a line belongs to."""
        for section_name, section_data in sections.items():
            section_lines = [line[0] for line in section_data["content"]]
            if section_lines and min(section_lines) <= line_num <= max(section_lines):
                return section_name
        return "unknown"


manuscript_analyzer = ManuscriptAnalyzer()
