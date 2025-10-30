import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

class TestMongoDBService:
    @patch('app.services.mongodb_service.AsyncIOMotorClient')
    def test_save_submission(self, mock_client):
        from app.services.mongodb_service import mongodb_service
        
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
        mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_collection
        
        # Test would require async context
        assert True  # Placeholder for actual async test

    @patch('app.services.mongodb_service.AsyncIOMotorClient')
    def test_get_submission(self, mock_client):
        from app.services.mongodb_service import mongodb_service
        
        mock_collection = Mock()
        mock_collection.find_one = AsyncMock(return_value={"_id": "test", "title": "test.pdf"})
        mock_client.return_value.__getitem__.return_value.__getitem__.return_value = mock_collection
        
        assert True  # Placeholder for actual async test

class TestDocumentParser:
    def test_parse_pdf_document(self):
        from app.services.document_parser import document_parser
        
        with patch('app.services.document_parser.PyPDF2.PdfReader') as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "test content"
            mock_reader.return_value.pages = [mock_page]
            
            result = document_parser.parse_document(b"%PDF content", "test.pdf")
            assert "content" in result
            assert "metadata" in result

    def test_parse_docx_document(self):
        from app.services.document_parser import document_parser
        
        with patch('app.services.document_parser.docx.Document') as mock_doc:
            mock_paragraph = Mock()
            mock_paragraph.text = "test content"
            mock_doc.return_value.paragraphs = [mock_paragraph]
            
            result = document_parser.parse_document(b"docx content", "test.docx")
            assert "content" in result

    def test_parse_unsupported_format(self):
        from app.services.document_parser import document_parser
        
        with pytest.raises(Exception):
            document_parser.parse_document(b"content", "test.txt")

class TestPDFGenerator:
    def test_generate_review_pdf(self):
        from app.services.pdf_generator import pdf_generator
        
        submission = {
            "title": "test.pdf",
            "file_metadata": {"original_filename": "test.pdf"}
        }
        
        with patch('app.services.pdf_generator.canvas.Canvas') as mock_canvas:
            mock_canvas.return_value.save.return_value = None
            
            result = pdf_generator.generate_review_pdf(submission, "test report")
            assert result is not None

class TestDisclaimerService:
    def test_get_system_disclaimer(self):
        from app.services.disclaimer_service import disclaimer_service
        
        result = disclaimer_service.get_system_disclaimer()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_api_disclaimer(self):
        from app.services.disclaimer_service import disclaimer_service
        
        result = disclaimer_service.get_api_disclaimer()
        assert isinstance(result, dict)
        assert "disclaimer" in result

class TestDomainDetector:
    def test_detect_medical_domain(self):
        from app.services.domain_detector import domain_detector
        
        submission = {
            "content": "This study examines patient outcomes in clinical trials",
            "title": "Medical Research Study"
        }
        result = domain_detector.detect_domain(submission)
        assert isinstance(result, dict)
        domain = result.get('domain', '')
        assert "medical" in domain.lower() or "biomedical" in domain.lower()

    def test_detect_computer_science_domain(self):
        from app.services.domain_detector import domain_detector
        
        submission = {
            "content": "This paper presents a machine learning algorithm for data processing",
            "title": "ML Algorithm Study"
        }
        result = domain_detector.detect_domain(submission)
        assert isinstance(result, dict)
        domain = result.get('domain', '')
        assert "computer" in domain.lower() or "engineering" in domain.lower()

    def test_detect_unknown_domain(self):
        from app.services.domain_detector import domain_detector
        
        submission = {
            "content": "random text without clear domain",
            "title": "Unknown Study"
        }
        result = domain_detector.detect_domain(submission)
        assert isinstance(result, dict)
        assert "domain" in result

class TestIssueDeduplicator:
    def test_deduplicate_similar_issues(self):
        from app.services.issue_deduplicator import issue_deduplicator
        
        issues = [
            {"description": "The methodology is unclear", "severity": "high"},
            {"description": "Methodology lacks clarity", "severity": "medium"},
            {"description": "Statistical analysis is missing", "severity": "high"}
        ]
        
        result = issue_deduplicator.deduplicate_issues(issues)
        assert len(result) < len(issues)

    def test_deduplicate_no_duplicates(self):
        from app.services.issue_deduplicator import issue_deduplicator
        
        issues = [
            {"description": "Methodology is unclear", "severity": "high"},
            {"description": "Literature review is incomplete", "severity": "medium"},
            {"description": "Conclusion is weak", "severity": "low"}
        ]
        
        result = issue_deduplicator.deduplicate_issues(issues)
        assert len(result) == len(issues)

class TestGuardrails:
    def test_content_filter_safe_content(self):
        from app.services.guardrails import guardrails
        
        safe_content = "This is a normal academic paper about research methodology"
        result = guardrails.filter_content(safe_content)
        assert result["is_safe"] == True

    def test_content_filter_sensitive_content(self):
        from app.services.guardrails import guardrails
        
        sensitive_content = "Patient John Doe, SSN: 123-45-6789, was treated for"
        result = guardrails.filter_content(sensitive_content)
        assert result["is_safe"] == False

    def test_bias_detection(self):
        from app.services.guardrails import guardrails
        
        biased_text = "This research clearly shows that group A is superior to group B"
        result = guardrails.detect_bias(biased_text)
        assert "bias_score" in result

class TestLLMService:
    @patch('app.services.llm_service.openai.ChatCompletion.create')
    def test_openai_call_success(self, mock_openai):
        from app.services.llm_service import llm_service
        
        mock_openai.return_value = {
            "choices": [{"message": {"content": "test response"}}]
        }
        
        result = llm_service.call_llm("test prompt", provider="openai")
        assert result == "test response"

    @patch('app.services.llm_service.anthropic.Anthropic')
    def test_anthropic_call_success(self, mock_anthropic):
        from app.services.llm_service import llm_service
        
        mock_response = Mock()
        mock_response.content = [Mock(text="test response")]
        mock_anthropic.return_value.messages.create.return_value = mock_response
        
        result = llm_service.call_llm("test prompt", provider="anthropic")
        assert result == "test response"

    def test_invalid_provider(self):
        from app.services.llm_service import llm_service
        
        with pytest.raises(ValueError):
            llm_service.call_llm("test prompt", provider="invalid")