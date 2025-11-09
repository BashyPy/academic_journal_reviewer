import html
import re
from typing import List, Tuple

from app.utils.logger import get_logger

logger = get_logger(__name__)


class TextAnalyzer:
    @staticmethod
    def find_line_number(full_text: str, target_text: str) -> int:
        """Find line number of target text."""
        if not full_text or not target_text:
            return 0
        start, _ = TextAnalyzer.find_text_position(full_text, target_text)
        if start == -1:
            return 0
        return full_text[:start].count("\n") + 1

    @staticmethod
    def find_text_position(full_text: str, target_text: str) -> Tuple[int, int]:
        """Find start and end positions of target text in full_text.

        Returns a tuple (start, end) or (-1, -1) if not found or on invalid input.

        Note: This function performs in-memory string matching only and does NOT
        construct or execute any database queries. Do not use return values from
        this function directly to build SQL/DB queries; always use parameterized
        queries or proper DB sanitization in database layers.
        """
        # Validate inputs
        if not isinstance(full_text, str) or not isinstance(target_text, str):
            return -1, -1

        if not full_text or not target_text:
            return -1, -1

        # Perform matching on raw text (do not escape before matching, escaping
        # is for output contexts such as HTML)
        start = full_text.find(target_text)
        if start == -1:
            # Try fuzzy matching for slight variations, but only on reasonably sized text
            # to avoid performance issues on very large documents.
            if len(full_text) < 500000:  # Limit fuzzy search to 500KB
                try:
                    start = TextAnalyzer._fuzzy_find(full_text, target_text)
                    # Assuming logger is defined elsewhere, if not, this will need adjustment.
                    # For now, we can remove the logging line if logger is not available.
                except Exception:
                    pass  # Ignore fuzzy find errors, start remains -1

        if start != -1 and target_text:
            return start, start + len(target_text)
        return -1, -1

    @staticmethod
    def _fuzzy_find(full_text: str, target_text: str) -> int:
        """Find text with minor variations (whitespace, punctuation)."""
        # Input validation
        if not isinstance(full_text, str) or not isinstance(target_text, str):
            return -1

        if not full_text or not target_text:
            return -1

        try:
            # Normalize whitespace for matching (case-insensitive)
            normalized_target = re.sub(r"\s+", " ", target_text.strip()).lower()
            normalized_full = re.sub(r"\s+", " ", full_text).lower()

            # Limit search size to prevent performance issues
            if len(normalized_full) > 100000:  # 100KB limit
                normalized_full = normalized_full[:100000]

            return normalized_full.find(normalized_target)
        except re.error as e:
            logger.error(f"Regex error during fuzzy find: {e}")
            return -1
        except Exception as e:
            logger.error(f"Unexpected error during fuzzy find: {e}")
            return -1

    @staticmethod
    def extract_context(
        full_text: str, start_pos: int, end_pos: int, context_length: int = 100
    ) -> str:
        """Extract surrounding context for highlighted text."""
        # Input validation
        if not isinstance(full_text, str) or not full_text:
            return ""

        if not isinstance(start_pos, int) or not isinstance(end_pos, int):
            return ""

        # If not found or invalid positions, return empty
        if start_pos < 0 or end_pos <= start_pos:
            return ""

        # Limit context length for security
        context_length = min(max(context_length, 0), 500)

        context_start = max(0, start_pos - context_length)
        context_end = min(len(full_text), end_pos + context_length)

        context = full_text[context_start:context_end]

        # Escape HTML to prevent XSS in output contexts
        context = html.escape(context)

        # Add ellipsis if truncated
        if context_start > 0:
            context = "..." + context
        if context_end < len(full_text):
            context += "..."

        return context

    @staticmethod
    def _is_valid_highlight_item(highlight: object) -> bool:
        return (
            isinstance(highlight, dict)
            and isinstance(highlight.get("text", ""), str)
            and bool(highlight.get("text", "").strip())
        )

    @staticmethod
    def _build_safe_highlight(full_text: str, highlight: dict, start: int, end: int) -> dict:
        safe = {
            "text": html.escape(highlight["text"]),
            "start_pos": start,
            "end_pos": end,
            "context": TextAnalyzer.extract_context(full_text, start, end),
        }
        # Only include explicitly defined fields to prevent information leaks.
        # The previous implementation copied any extra fields of certain types.
        return safe

    @staticmethod
    def validate_highlights(full_text: str, highlights: List[dict]) -> List[dict]:
        """Validate and correct highlight positions."""
        if not isinstance(full_text, str) or not isinstance(highlights, list):
            return []

        if not full_text or not highlights:
            return []

        validated: List[dict] = []
        max_highlights = 100

        for highlight in highlights[:max_highlights]:
            if not TextAnalyzer._is_valid_highlight_item(highlight):
                continue

            text = highlight["text"]
            if len(text) > 1000:
                continue

            try:
                start, end = TextAnalyzer.find_text_position(full_text, text)
            except Exception as e:
                logger.warning(f"Could not process highlight for text: '{text[:100]}'. Error: {e}")
                continue

            if start == -1 or end == -1:
                continue

            validated.append(TextAnalyzer._build_safe_highlight(full_text, highlight, start, end))

        return validated
