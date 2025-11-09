import re
from typing import Dict, List, Optional, Pattern, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


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
                logger.warning(f"Invalid regex pattern in section_patterns: {pattern} ({str(e)})")

    def _detect_section_header(self, stripped: str) -> Optional[str]:
        """Return the section name if the stripped line matches a header, otherwise None."""
        if not stripped or len(stripped) >= 100:
            return None
        for section_name, compiled in self.compiled_section_patterns:
            if compiled.search(stripped):
                return section_name
        return None

    def _ensure_section(self, sections: Dict[str, Dict], section_name: str, line_num: int) -> None:
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

            # Track min and max line numbers for each section for efficient lookup
            if "min_line" not in sections[current_section]:
                sections[current_section]["min_line"] = line_num
                sections[current_section]["max_line"] = line_num
            else:
                sections[current_section]["min_line"] = min(
                    sections[current_section]["min_line"], line_num
                )
                sections[current_section]["max_line"] = max(
                    sections[current_section]["max_line"], line_num
                )

        return sections

    def get_section_for_line(self, sections: Dict, line_num: int) -> str:
        """Determine which section a line belongs to."""
        for section_name, section_data in sections.items():
            min_line = section_data.get("min_line")
            max_line = section_data.get("max_line")
            if min_line is not None and max_line is not None and min_line <= line_num <= max_line:
                return section_name
        return "unknown"


manuscript_analyzer = ManuscriptAnalyzer()
