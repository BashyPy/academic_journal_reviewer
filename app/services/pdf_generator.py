import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.utils.logger import get_logger

# Constant for repeated report title
DEFAULT_REPORT_TITLE = "Academic Review Report"


class PDFReportGenerator:
    """Generate simple academic PDF review reports using ReportLab with defensive error handling."""

    def __init__(self) -> None:
        # Logger for error reporting and debugging
        self.logger = get_logger(__name__)
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
        except ValueError as e:
            style_name = getattr(style, "name", "unknown")
            self.logger.error(
                f"Failed to create Paragraph with style {style_name}, fallback to Normal: {e}",
                extra={"component": "pdf_generator", "function": "_safe_paragraph"},
            )
            return Paragraph(self._escape_text(text), self.styles["Normal"])

    def _escape_text(self, text: str) -> str:
        # Minimal escaping to avoid ReportLab markup errors
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def generate_pdf_report(self, review_content: str, submission_info: Dict[str, Any]) -> BytesIO:
        """
        Generate a PDF report from review_content and submission_info.
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
        # Header
        title = submission_info.get("title", "Untitled Manuscript")
        story.append(self._safe_paragraph(DEFAULT_REPORT_TITLE, self.styles["AcademicReportTitle"]))
        story.append(Spacer(1, 10))
        story.append(
            self._safe_paragraph(
                f"<b>Manuscript:</b> {self._escape_text(str(title))}",
                self.styles["AcademicBodyText"],
            )
        )
        if "authors" in submission_info:
            authors = submission_info["authors"]
            story.append(
                self._safe_paragraph(
                    f"<b>Authors:</b> {self._escape_text(str(authors))}",
                    self.styles["AcademicBodyText"],
                )
            )
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(
            self._safe_paragraph(f"<b>Review Date:</b> {date_str}", self.styles["AcademicBodyText"])
        )
        story.append(Spacer(1, 20))

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
            "<b>⚠️ HUMAN OVERSIGHT REQUIRED:</b> This AI-generated review is for "
            "preliminary assessment only. Human expert validation is mandatory before "
            "any editorial decisions. Do not use for final publication decisions without "
            "qualified human reviewer approval."
        )

        story.append(self._safe_paragraph(disclaimer_text, disclaimer_style))
        story.append(Spacer(1, 20))

        # Parse and format content
        if not review_content or review_content.strip() == "":
            story.append(
                self._safe_paragraph(
                    "Review failed due to system error. Please try again or contact support.",
                    self.styles["AcademicBodyText"],
                )
            )
        else:
            try:
                parsed = self._parse_review_content(review_content)
                if parsed and isinstance(parsed, list):
                    story.extend(parsed)
                else:
                    story.append(
                        self._safe_paragraph(review_content, self.styles["AcademicBodyText"])
                    )
            except Exception:
                self.logger.error(
                    Exception("Failed to parse review content; using raw content"),
                    {"component": "pdf_generator", "function": "generate_pdf_report"},
                )
                story.append(self._safe_paragraph(review_content, self.styles["AcademicBodyText"]))

        # Footer
        story.append(Spacer(1, 30))
        footer_text = (
            "This review was generated by the Academic Agentic Review Intelligence "
            "System (AARIS). The analysis combines multiple specialized AI agents to "
            "provide comprehensive academic evaluation."
        )
        story.append(self._safe_paragraph(footer_text, self.styles["Normal"]))

        # Build document
        try:
            doc.build(story)
            buffer.seek(0)
            return buffer
        except Exception as e:
            self.logger.error(e, {"component": "pdf_generator", "function": "generate_pdf_report"})
            raise RuntimeError("PDF generation failed") from e

    def _parse_review_content(self, content: str) -> list:
        elements: List[Any] = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if not self._handle_special_line(line, elements):
                # Regular paragraphs (fallback)
                clean_line = self._clean_markdown(line)
                elements.append(self._safe_paragraph(clean_line, self.styles["AcademicBodyText"]))

        return elements

    def _handle_special_line(self, line: str, elements: list) -> bool:
        # Handles section headers, subsections, bullets and numbered lists.
        # Returns True if handled, False otherwise.
        if line.startswith("## "):
            header = line[3:].strip()
            elements.append(self._safe_paragraph(header, self.styles["AcademicSectionHeader"]))
            return True

        if line.startswith("### "):
            header = line[4:].strip()
            elements.append(self._safe_paragraph(header, self.styles["AcademicSubHeader"]))
            return True

        # Handle Line-by-Line Recommendations with better formatting
        if line.startswith("**Line ") or (line.startswith("Line ") and ":" in line):
            clean_line = self._clean_markdown(line)
            # Use a more prominent style for line-specific findings
            elements.append(self._safe_paragraph(clean_line, self.styles["AcademicBodyText"]))
            elements.append(Spacer(1, 4))  # Add small space after each finding
            return True

        if line.startswith("- "):
            bullet_text = line[2:].strip()
            clean_bullet = self._clean_markdown(bullet_text)
            elements.append(
                self._safe_paragraph(f"• {clean_bullet}", self.styles["AcademicIssueText"])
            )
            return True

        if re.match(r"^\d+\.", line):
            clean_line = self._clean_markdown(line)
            elements.append(self._safe_paragraph(clean_line, self.styles["AcademicIssueText"]))
            return True

        return False

    def _process_section(self, section_lines: list) -> list:
        elements: List[Any] = []
        for line in section_lines:
            if line.strip():
                clean_line = self._clean_markdown(line)
                elements.append(self._safe_paragraph(clean_line, self.styles["AcademicBodyText"]))
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
            self.logger.error(
                Exception("Failed to clean markdown text; returning escaped text"),
                {"component": "pdf_generator", "function": "_clean_markdown"},
            )
            return self._escape_text(text)

    def generate_review_pdf(self, submission: Dict[str, Any], review_content: str) -> BytesIO:
        """Generate PDF for review report - matches API call signature"""
        if not isinstance(submission, dict):
            raise TypeError("Submission must be a dictionary")
        if not isinstance(review_content, str):
            review_content = str(review_content) if review_content else "No content available"

        return self.generate_pdf_report(review_content, submission)


pdf_generator = PDFReportGenerator()
