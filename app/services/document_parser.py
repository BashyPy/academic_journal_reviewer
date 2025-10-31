import io
from typing import Any, Dict

import PyPDF2
from docx import Document

from app.utils.logger import get_logger


class DocumentParser:
    def __init__(self):
        self.logger = get_logger()

    def parse_pdf(self, file_content: bytes) -> Dict[str, Any]:
        try:
            if not isinstance(file_content, (bytes, bytearray)) or not file_content:
                raise ValueError("Invalid or empty PDF content")

            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            except Exception as e:
                # Log and wrap low-level PDF read errors
                self.logger.exception("Failed to read PDF stream")
                raise ValueError("Failed to read PDF file") from e

            num_pages = len(getattr(pdf_reader, "pages", []))
            if num_pages == 0:
                raise ValueError("PDF contains no pages")

            # Use list accumulation for better performance than repeated string concatenation
            text_parts = []
            for i, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    # Non-fatal per-page extraction failures should be logged and skipped
                    self.logger.warning(f"Failed to extract text from page {i+1}: {e}")
                    continue

            text = "\n".join(text_parts).strip()

            if not text:
                raise ValueError("No text could be extracted from PDF")

            return {
                "content": text,
                "metadata": {"pages": num_pages, "file_type": "pdf"},
            }
        except ValueError:
            # ValueErrors are expected validation/parsing errors — already logged where appropriate
            raise
        except Exception as e:
            # Catch-all for unexpected errors: log with traceback and preserve context
            self.logger.exception("Unexpected error while parsing PDF")
            raise ValueError(f"Failed to parse PDF: {e}") from e

    def parse_docx(self, file_content: bytes) -> Dict[str, Any]:
        try:
            if not file_content or len(file_content) < 100:
                raise ValueError("Invalid or empty DOCX content")

            doc = Document(io.BytesIO(file_content))

            paragraphs = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)

            text = "\n".join(paragraphs)

            if not text.strip():
                raise ValueError("No text could be extracted from DOCX")

            return {
                "content": text.strip(),
                "metadata": {"paragraphs": len(paragraphs), "file_type": "docx"},
            }
        except Exception as e:
            self.logger.error(e, additional_info={"parser_type": "docx"})
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    def parse_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        try:
            if not isinstance(file_content, bytes) or not file_content:
                raise ValueError("Invalid file content")

            if not isinstance(filename, str) or not filename:
                raise ValueError("Invalid filename")

            filename_lower = filename.lower()
            if filename_lower.endswith(".pdf"):
                return self.parse_pdf(file_content)
            elif filename_lower.endswith(".docx"):
                return self.parse_docx(file_content)
            else:
                raise ValueError(f"Unsupported file type: {filename}")
        except Exception as e:
            self.logger.error(
                e,
                additional_info={
                    "filename": filename,
                    "content_size": len(file_content) if file_content else 0,
                },
            )
            raise


document_parser = DocumentParser()
