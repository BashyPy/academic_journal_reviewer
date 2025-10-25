import io
from typing import Any, Dict

import PyPDF2
from docx import Document


class DocumentParser:
    @staticmethod
    def parse_pdf(file_content: bytes) -> Dict[str, Any]:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"

        return {
            "content": text.strip(),
            "metadata": {"pages": len(pdf_reader.pages), "file_type": "pdf"},
        }

    @staticmethod
    def parse_docx(file_content: bytes) -> Dict[str, Any]:
        doc = Document(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])

        return {
            "content": text.strip(),
            "metadata": {"paragraphs": len(doc.paragraphs), "file_type": "docx"},
        }

    @classmethod
    def parse_document(cls, file_content: bytes, filename: str) -> Dict[str, Any]:
        if filename.lower().endswith(".pdf"):
            return cls.parse_pdf(file_content)
        elif filename.lower().endswith(".docx"):
            return cls.parse_docx(file_content)
        else:
            raise ValueError(f"Unsupported file type: {filename}")


document_parser = DocumentParser()
