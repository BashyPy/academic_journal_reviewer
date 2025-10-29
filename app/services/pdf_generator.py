from typing import Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from io import BytesIO
import re
from datetime import datetime
from app.services.disclaimer_service import disclaimer_service


class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        # Custom styles for academic reports
        self.styles.add(ParagraphStyle(
            name='AcademicReportTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        ))
        
        self.styles.add(ParagraphStyle(
            name='AcademicSectionHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10
        ))
        
        self.styles.add(ParagraphStyle(
            name='AcademicSubHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=8
        ))
        
        self.styles.add(ParagraphStyle(
            name='AcademicBodyText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leftIndent=0.2*inch
        ))
        
        self.styles.add(ParagraphStyle(
            name='AcademicIssueText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leftIndent=0.4*inch,
            bulletIndent=0.2*inch
        ))

    def generate_pdf_report(self, review_content: str, submission_info: Dict[str, Any]) -> BytesIO:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=1*inch
        )
        
        story = []
        
        # Header with disclaimer
        story.extend(self._create_header(submission_info))
        story.append(Spacer(1, 10))
        
        # Add prominent disclaimer at top
        disclaimer_style = ParagraphStyle(
            name='DisclaimerStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=15,
            leftIndent=0.5*inch,
            rightIndent=0.5*inch,
            borderWidth=1,
            borderPadding=10
        )
        
        disclaimer_text = (
            "<b>⚠️ HUMAN OVERSIGHT REQUIRED:</b> This AI-generated review is for preliminary assessment only. "
            "Human expert validation is mandatory before any editorial decisions. "
            "Do not use for final publication decisions without qualified human reviewer approval."
        )
        
        story.append(Paragraph(disclaimer_text, disclaimer_style))
        story.append(Spacer(1, 20))
        
        # Parse and format content
        story.extend(self._parse_review_content(review_content))
        
        # Footer
        story.append(Spacer(1, 30))
        story.extend(self._create_footer())
        
        doc.build(story)
        buffer.seek(0)
        return buffer

    def _create_header(self, submission_info: Dict[str, Any]) -> list:
        elements = []
        
        # Title
        title = submission_info.get('title', 'Academic Review Report')
        elements.append(Paragraph("Academic Review Report", self.styles['AcademicReportTitle']))
        elements.append(Spacer(1, 10))
        
        # Manuscript info
        elements.append(Paragraph(f"<b>Manuscript:</b> {title}", self.styles['AcademicBodyText']))
        
        if 'authors' in submission_info:
            authors = submission_info['authors']
            elements.append(Paragraph(f"<b>Authors:</b> {authors}", self.styles['AcademicBodyText']))
        
        # Date
        date_str = datetime.now().strftime("%B %d, %Y")
        elements.append(Paragraph(f"<b>Review Date:</b> {date_str}", self.styles['AcademicBodyText']))
        
        return elements

    def _parse_review_content(self, content: str) -> list:
        elements = []
        lines = content.split('\n')
        current_section = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            handled, current_section = self._handle_special_line(line, elements, current_section)
            if handled:
                continue

            # Regular paragraphs (fallback)
            clean_line = self._clean_markdown(line)
            elements.append(Paragraph(clean_line, self.styles['AcademicBodyText']))

        # Process any remaining section
        if current_section:
            elements.extend(self._process_section(current_section))

        return elements

    def _handle_special_line(self, line: str, elements: list, current_section: list) -> tuple:
        # Handles section headers, subsections, bullets and numbered lists.
        # Returns (handled: bool, current_section: list)
        if line.startswith('## '):
            if current_section:
                elements.extend(self._process_section(current_section))
                current_section = []
            header = line[3:].strip()
            elements.append(Paragraph(header, self.styles['AcademicSectionHeader']))
            return True, current_section

        if line.startswith('### '):
            header = line[4:].strip()
            elements.append(Paragraph(header, self.styles['AcademicSubHeader']))
            return True, current_section

        # Handle Line-by-Line Recommendations with better formatting
        if line.startswith('Line ') and ':' in line:
            clean_line = self._clean_markdown(line)
            elements.append(Paragraph(clean_line, self.styles['AcademicIssueText']))
            return True, current_section

        if line.startswith('- '):
            bullet_text = line[2:].strip()
            clean_bullet = self._clean_markdown(bullet_text)
            elements.append(Paragraph(f"• {clean_bullet}", self.styles['AcademicIssueText']))
            return True, current_section

        if re.match(r'^\d+\.', line):
            clean_line = self._clean_markdown(line)
            elements.append(Paragraph(clean_line, self.styles['AcademicIssueText']))
            return True, current_section

        return False, current_section

    def _process_section(self, section_lines: list) -> list:
        elements = []
        for line in section_lines:
            if line.strip():
                clean_line = self._clean_markdown(line)
                elements.append(Paragraph(clean_line, self.styles['AcademicBodyText']))
        return elements

    def _clean_markdown(self, text: str) -> str:
        # Convert markdown formatting to HTML for ReportLab
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # Bold
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # Italic
        text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)  # Code
        
        # Clean up any remaining markdown
        text = text.replace('**', '').replace('*', '')
        
        return text

    def _create_footer(self) -> list:
        elements = []
        elements.append(Spacer(1, 20))
        
        footer_text = (
            "This review was generated by the Academic Agentic Review Intelligence System (AARIS). "
            "The analysis combines multiple specialized AI agents to provide comprehensive academic evaluation."
        )
        
        elements.append(Paragraph(footer_text, self.styles['Normal']))
        return elements
    
    def generate_review_pdf(self, submission: Dict[str, Any], review_content: str) -> BytesIO:
        """Generate PDF for review report - matches API call signature"""
        return self.generate_pdf_report(review_content, submission)


pdf_generator = PDFReportGenerator()