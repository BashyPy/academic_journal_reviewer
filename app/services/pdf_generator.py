from typing import Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from io import BytesIO
import re
from datetime import datetime


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
        
        # Header
        story.extend(self._create_header(submission_info))
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
        elements.append(Paragraph(f"Academic Review Report", self.styles['AcademicReportTitle']))
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
                
            # Section headers (##)
            if line.startswith('## '):
                if current_section:
                    elements.extend(self._process_section(current_section))
                    current_section = []
                
                header = line[3:].strip()
                elements.append(Paragraph(header, self.styles['AcademicSectionHeader']))
                
            # Subsection headers (###)
            elif line.startswith('### '):
                header = line[4:].strip()
                elements.append(Paragraph(header, self.styles['AcademicSubHeader']))
                
            # Bullet points
            elif line.startswith('- '):
                bullet_text = line[2:].strip()
                elements.append(Paragraph(f"• {bullet_text}", self.styles['AcademicIssueText']))
                
            # Numbered lists
            elif re.match(r'^\d+\.', line):
                elements.append(Paragraph(line, self.styles['AcademicIssueText']))
                
            # Regular paragraphs
            else:
                if line:
                    # Clean up markdown formatting
                    clean_line = self._clean_markdown(line)
                    elements.append(Paragraph(clean_line, self.styles['AcademicBodyText']))
        
        # Process any remaining section
        if current_section:
            elements.extend(self._process_section(current_section))
        
        return elements

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