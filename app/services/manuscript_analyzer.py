import re
from typing import Dict, Optional


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

    def analyze_structure(self, content: str) -> Dict[str, Dict]:
        """Analyze manuscript structure and identify sections."""
        lines = content.split("\n")
        sections = {}
        current_section = "unknown"

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            if not stripped:
                continue

            # Check for section headers
            for section_name, pattern in self.section_patterns.items():
                if re.search(pattern, stripped) and len(stripped) < 100:
                    current_section = section_name
                    if section_name not in sections:
                        sections[section_name] = {
                            "start_line": line_num,
                            "content": [],
                            "word_count": 0,
                        }
                    break

            # Add content to current section
            if current_section not in sections:
                sections[current_section] = {
                    "start_line": line_num,
                    "content": [],
                    "word_count": 0,
                }

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
