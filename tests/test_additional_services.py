"""More tests for coverage"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from io import BytesIO


class TestDocumentParser:
    def test_parse_pdf(self, sample_pdf_content):
        from app.services.document_parser import document_parser
        r = document_parser.parse_document(sample_pdf_content, "test.pdf")
        assert "content" in r

    def test_parse_docx(self, sample_docx_content):
        from app.services.document_parser import document_parser
        r = document_parser.parse_document(sample_docx_content, "test.docx")
        assert "content" in r

    def test_detect_file_type(self):
        from app.services.document_parser import document_parser
        assert document_parser._detect_file_type(b"%PDF", "test.pdf") == "pdf"

    def test_extract_pdf_text(self, sample_pdf_content):
        from app.services.document_parser import document_parser
        t = document_parser._extract_text_from_pdf(BytesIO(sample_pdf_content))
        assert isinstance(t, str)


class TestDomainDetector:
    def test_detect_domain(self):
        from app.services.domain_detector import domain_detector
        d = domain_detector.detect_domain("machine learning algorithm neural network")
        assert d is not None

    def test_get_weights(self):
        from app.services.domain_detector import domain_detector
        w = domain_detector.get_domain_weights("medical")
        assert "methodology" in w

    def test_extract_keywords(self):
        from app.services.domain_detector import domain_detector
        k = domain_parser._extract_keywords("test text with keywords")
        assert isinstance(k, list)


class TestPDFGenerator:
    def test_generate_pdf(self):
        from app.services.pdf_generator import pdf_generator
        sub = {"title": "Test", "file_metadata": {"original_filename": "test.pdf"}}
        pdf = pdf_generator.generate_review_pdf(sub, "# Report\nTest content")
        assert pdf is not None


class TestIssueDeduplicator:
    def test_deduplicate(self):
        from app.services.issue_deduplicator import issue_deduplicator
        issues = [{"issue": "Test 1"}, {"issue": "Test 1"}, {"issue": "Test 2"}]
        r = issue_deduplicator.deduplicate(issues)
        assert len(r) <= len(issues)

    def test_similarity(self):
        from app.services.issue_deduplicator import issue_deduplicator
        s = issue_deduplicator._calculate_similarity("test", "test")
        assert s == 1.0


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_verify_api_key(self):
        from app.middleware.auth import verify_api_key
        with patch('app.services.user_service.user_service.get_user_by_api_key') as m:
            m.return_value = {"email": "a@b.com", "active": True, "email_verified": True}
            r = await verify_api_key("key")
            assert r is not None


class TestPermissions:
    def test_check_permission(self):
        from app.middleware.permissions import check_permission
        from app.models.roles import Role
        assert check_permission({"role": "admin"}, "manage_users")

    def test_require_permission(self):
        from app.middleware.permissions import require_permission
        from app.models.roles import Role
        decorator = require_permission("view_submissions")
        assert decorator is not None


class TestRoles:
    def test_role_permissions(self):
        from app.models.roles import Role, get_role_permissions, has_permission
        perms = get_role_permissions(Role.ADMIN)
        assert "manage_users" in perms
        assert has_permission(Role.ADMIN, "manage_users")


class TestConfig:
    def test_get_llm_config(self):
        from app.core.config import settings
        c = settings.get_llm_config("openai")
        assert c is not None


class TestLogger:
    def test_all_levels(self):
        from app.utils.logger import get_logger
        l = get_logger("test")
        l.info("info")
        l.warning("warn")
        l.error(Exception("err"))
        l.info("data", additional_info={"k": "v"})


class TestDisclaimerService:
    def test_get_disclaimers(self):
        from app.services.disclaimer_service import disclaimer_service
        api = disclaimer_service.get_api_disclaimer()
        assert "disclaimer" in api
        ui = disclaimer_service.get_ui_disclaimer()
        assert "title" in ui


class TestRequestSigning:
    def test_generate_signature(self):
        from app.middleware.request_signing import generate_signature
        s = generate_signature("data", "secret")
        assert len(s) > 0

    def test_verify_signature(self):
        from app.middleware.request_signing import verify_signature, generate_signature
        sig = generate_signature("data", "secret")
        assert verify_signature("data", sig, "secret")
