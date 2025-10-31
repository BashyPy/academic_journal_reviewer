import logging
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

# Constant for repeated report title
DEFAULT_REPORT_TITLE = "Academic Review Report"

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


class PDFReportGenerator:
    """Generate simple academic PDF review reports using ReportLab with defensive error handling."""

    def __init__(self) -> None:
        # Logger for error reporting and debugging
        self.logger = logging.getLogger(__name__)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        # Custom styles for academic reports
        self.styles.add(
            ParagraphStyle(
                name="AcademicReportTitle",
                parent=self.styles["Title"],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="AcademicSectionHeader",
                parent=self.styles["Heading1"],
                fontSize=14,
                spaceBefore=15,
                spaceAfter=10,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="AcademicSubHeader",
                parent=self.styles["Heading2"],
                fontSize=12,
                spaceBefore=10,
                spaceAfter=8,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="AcademicBodyText",
                parent=self.styles["Normal"],
                fontSize=11,
                spaceAfter=8,
                alignment=TA_JUSTIFY,
                leftIndent=0.2 * inch,
            )
        )

        # Complete style definition with proper closing parentheses
        self.styles.add(
            ParagraphStyle(
                name="AcademicIssueText",
                parent=self.styles["Normal"],
                fontSize=10,
                spaceAfter=6,
                leftIndent=0.4 * inch,
                bulletIndent=0.2 * inch,
            )
        )

    def _safe_paragraph(self, text: str, style: ParagraphStyle) -> Paragraph:
        """
        Create a Paragraph while guarding against ReportLab exceptions;
        fall back to a safe plain-text paragraph if necessary.
        """
        try:
            return Paragraph(text, style)
        except Exception:
            self.logger.exception(
                "Failed to create Paragraph with style %s, falling back to Normal",
                getattr(style, "name", "unknown"),
            )
            return Paragraph(self._escape_text(text), self.styles["Normal"])

    def _escape_text(self, text: str) -> str:
        # Minimal escaping to avoid ReportLab markup errors
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def generate_pdf_report(
        self, review_content: str, submission_info: Dict[str, Any]
    ) -> BytesIO:
        """
        Generate a PDF report from review_content and submission_info with validation and robust error handling.
        """
        # Validate inputs early to fail fast with clear errors
        if not isinstance(review_content, str):
            raise TypeError("review_content must be a string")
        if not isinstance(submission_info, dict):
            raise TypeError("submission_info must be a dict")

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )
        # Initialize the story flowable list before use
        story: List[Any] = []
        # Header with robust error handling
        try:
            story.extend(self._create_header(submission_info))
        except Exception:
            self.logger.exception(
                "Failed to create PDF header; continuing with minimal header"
            )
            # Add a minimal header so PDF still generates
            story.append(
                self._safe_paragraph(
                    DEFAULT_REPORT_TITLE, self.styles["AcademicReportTitle"]
                )
            )
            story.append(Spacer(1, 10))
            # Add a minimal header so PDF still generates
            story.append(
                self._safe_paragraph(
                    DEFAULT_REPORT_TITLE, self.styles["AcademicReportTitle"]
                )
            )
            story.append(Spacer(1, 10))

        story.append(Spacer(1, 10))

        # Add prominent disclaimer at top — keep style attributes to those supported by ReportLab
        disclaimer_style = ParagraphStyle(
            name="DisclaimerStyle",
            parent=self.styles["Normal"],
            fontSize=10,
            spaceAfter=15,
            leftIndent=0.5 * inch,
            rightIndent=0.5 * inch,
        )

        disclaimer_text = (
            "<b>⚠️ HUMAN OVERSIGHT REQUIRED:</b> This AI-generated review is for preliminary assessment only. "
            "Human expert validation is mandatory before any editorial decisions. "
            "Do not use for final publication decisions without qualified human reviewer approval."
        )

        story.append(self._safe_paragraph(disclaimer_text, disclaimer_style))
        story.append(Spacer(1, 20))

        # Parse and format content with defensive checks
        try:
            parsed = self._parse_review_content(review_content)
            if not isinstance(parsed, list):
                raise RuntimeError("Parsed review content must be a list of flowables")
            story.extend(parsed)
        except Exception:
            self.logger.exception(
                "Failed to parse review content; inserting error notice into PDF"
            )
            story.append(
                self._safe_paragraph(
                    "Unable to parse review content. See server logs for details.",
                    self.styles["AcademicBodyText"],
                )
            )

        # Footer
        story.append(Spacer(1, 30))
        try:
            footer = self._create_footer()
            if not isinstance(footer, list):
                raise RuntimeError("Footer must be a list of flowables")
            story.extend(footer)
        except Exception:
            self.logger.exception("Failed to create footer; adding minimal footer")
            story.append(
                self._safe_paragraph(
                    "Generated by Academic Review Generator.", self.styles["Normal"]
                )
            )

        # Build document with error handling and clear exception propagation
        try:
            doc.build(story)
            buffer.seek(0)
            return buffer
        except Exception as e:
            self.logger.exception("Failed to build PDF document", exc_info=e)
            raise RuntimeError("PDF generation failed") from e

        # Title
        title = submission_info.get("title", DEFAULT_REPORT_TITLE)
        elements.append(
            self._safe_paragraph(
                DEFAULT_REPORT_TITLE, self.styles["AcademicReportTitle"]
            )
        )
        elements.append(Spacer(1, 10))
        title = submission_info.get("title", DEFAULT_REPORT_TITLE)
        elements.append(
            self._safe_paragraph(
                DEFAULT_REPORT_TITLE, self.styles["AcademicReportTitle"]
            )
        )
        elements.append(Spacer(1, 10))

        # Manuscript info
        try:
            elements.append(
                self._safe_paragraph(
                    f"<b>Manuscript:</b> {self._escape_text(str(title))}",
                    self.styles["AcademicBodyText"],
                )
            )
        except Exception:
            self.logger.exception("Failed to add manuscript info to header")

        if "authors" in submission_info:
            try:
                authors = submission_info["authors"]
                elements.append(
                    self._safe_paragraph(
                        f"<b>Authors:</b> {self._escape_text(str(authors))}",
                        self.styles["AcademicBodyText"],
                    )
                )
            except Exception:
                self.logger.exception("Failed to add authors to header")

        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        elements.append(
            self._safe_paragraph(
                f"<b>Review Date:</b> {date_str}", self.styles["AcademicBodyText"]
            )
        )

        return elements

    def _parse_review_content(self, content: str) -> list:
        elements: List[Any] = []
        lines = content.split("\n")
        current_section: List[str] = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            handled, current_section = self._handle_special_line(
                line, elements, current_section
            )
            if handled:
                continue

            # Regular paragraphs (fallback)
            clean_line = self._clean_markdown(line)
            elements.append(
                self._safe_paragraph(clean_line, self.styles["AcademicBodyText"])
            )

        # Process any remaining section
        if current_section:
            elements.extend(self._process_section(current_section))

        return elements

    def _handle_special_line(
        self, line: str, elements: list, current_section: list
    ) -> tuple:
        # Handles section headers, subsections, bullets and numbered lists.
        # Returns (handled: bool, current_section: list)
        if line.startswith("## "):
            if current_section:
                elements.extend(self._process_section(current_section))
                current_section = []
            header = line[3:].strip()
            elements.append(
                self._safe_paragraph(header, self.styles["AcademicSectionHeader"])
            )
            return True, current_section

        if line.startswith("### "):
            header = line[4:].strip()
            elements.append(
                self._safe_paragraph(header, self.styles["AcademicSubHeader"])
            )
            return True, current_section

        # Handle Line-by-Line Recommendations with better formatting
        if line.startswith("Line ") and ":" in line:
            clean_line = self._clean_markdown(line)
            elements.append(
                self._safe_paragraph(clean_line, self.styles["AcademicIssueText"])
            )
            return True, current_section

        if line.startswith("- "):
            bullet_text = line[2:].strip()
            clean_bullet = self._clean_markdown(bullet_text)
            elements.append(
                self._safe_paragraph(
                    f"• {clean_bullet}", self.styles["AcademicIssueText"]
                )
            )
            return True, current_section

        if re.match(r"^\d+\.", line):
            clean_line = self._clean_markdown(line)
            elements.append(
                self._safe_paragraph(clean_line, self.styles["AcademicIssueText"])
            )
            return True, current_section

        return False, current_section

    def _process_section(self, section_lines: list) -> list:
        elements: List[Any] = []
        for line in section_lines:
            if line.strip():
                clean_line = self._clean_markdown(line)
                elements.append(
                    self._safe_paragraph(clean_line, self.styles["AcademicBodyText"])
                )
        return elements

    def _clean_markdown(self, text: str) -> str:
        # Convert markdown formatting to simple HTML for ReportLab
        try:
            original = text
            text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)  # Bold
            text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)  # Italic
            text = re.sub(r"`(.*?)`", r'<font name="Courier">\1</font>', text)  # Code
            # Avoid removing brackets used in HTML tags we intentionally produce
            # Minimal cleanup

            # If no transformation occurred, return a safely escaped version
            if text == original:
                return self._escape_text(text)

            return text
        except Exception:
            self.logger.exception(
                "Failed to clean markdown text; returning escaped text"
            )
            return self._escape_text(text)

    def _create_footer(self) -> list:
        elements: List[Any] = []
        elements.append(Spacer(1, 20))

        footer_text = (
            "This review was generated by the Academic Agentic Review Intelligence System (AARIS). "
            "The analysis combines multiple specialized AI agents to provide comprehensive academic evaluation."
        )

        elements.append(self._safe_paragraph(footer_text, self.styles["Normal"]))
        return elements

    def generate_review_pdf(
        self, submission: Dict[str, Any], review_content: str
    ) -> BytesIO:
        """Generate PDF for review report - matches API call signature"""
        return self.generate_pdf_report(review_content, submission)


pdf_generator = PDFReportGenerator()
