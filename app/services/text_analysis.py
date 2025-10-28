import re
from typing import List, Tuple


class TextAnalyzer:
    @staticmethod
    def find_text_position(full_text: str, target_text: str) -> Tuple[int, int]:
        """Find start and end positions of target text in full text."""
        start = full_text.find(target_text)
        if start == -1:
            # Try fuzzy matching for slight variations
            start = TextAnalyzer._fuzzy_find(full_text, target_text)

        if start != -1:
            return start, start + len(target_text)
        return 0, 0

    @staticmethod
    def _fuzzy_find(full_text: str, target_text: str) -> int:
        """Find text with minor variations (whitespace, punctuation)."""
        # Normalize whitespace and punctuation for matching
        normalized_target = re.sub(r"\s+", " ", target_text.strip())
        normalized_full = re.sub(r"\s+", " ", full_text)

        return normalized_full.find(normalized_target)

    @staticmethod
    def extract_context(
        full_text: str, start_pos: int, end_pos: int, context_length: int = 100
    ) -> str:
        """Extract surrounding context for highlighted text."""
        context_start = max(0, start_pos - context_length)
        context_end = min(len(full_text), end_pos + context_length)

        context = full_text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(full_text):
            context = context + "..."

        return context

    @staticmethod
    def validate_highlights(full_text: str, highlights: List[dict]) -> List[dict]:
        """Validate and correct highlight positions."""
        validated = []

        for highlight in highlights:
            text = highlight.get("text", "")
            if not text:
                continue

            start, end = TextAnalyzer.find_text_position(full_text, text)
            if start != 0 or end != 0:
                highlight["start_pos"] = start
                highlight["end_pos"] = end
                highlight["context"] = TextAnalyzer.extract_context(
                    full_text, start, end
                )
                validated.append(highlight)

        return validated
