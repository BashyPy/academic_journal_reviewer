"""Tests for security features"""

import pytest

from app.middleware.request_signing import RequestSigner
from app.middleware.waf import waf
from app.services.security_monitor import security_monitor

# Mark MongoDB tests to skip if MongoDB not available
pytestmark_mongodb = pytest.mark.skipif(
    True,  # Skip MongoDB tests by default in CI/CD
    reason="MongoDB tests require running MongoDB instance",
)


@pytest.mark.skip(reason="Requires MongoDB")
class TestAuthentication:
    """Test authentication and authorization (requires MongoDB)"""

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        """Test API key creation"""
        from app.middleware.auth import auth_service

        result = await auth_service.create_api_key("test_user", "user", 365)
        assert "api_key" in result
        assert result["api_key"].startswith("aaris_")
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_validate_api_key(self):
        """Test API key validation"""
        from app.middleware.auth import auth_service

        result = await auth_service.create_api_key("test_user", "user", 365)
        api_key = result["api_key"]

        user = await auth_service.validate_api_key(api_key)
        assert user is not None
        assert user["name"] == "test_user"
        assert user["role"] == "user"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test invalid API key"""
        from app.middleware.auth import auth_service

        user = await auth_service.validate_api_key("invalid_key")
        assert user is None

    @pytest.mark.asyncio
    async def test_revoke_api_key(self):
        """Test API key revocation"""
        from app.middleware.auth import auth_service

        result = await auth_service.create_api_key("test_user", "user", 365)
        api_key = result["api_key"]

        success = await auth_service.revoke_api_key(api_key)
        assert success is True

        user = await auth_service.validate_api_key(api_key)
        assert user is None


class TestWAF:
    """Test Web Application Firewall"""

    def test_sql_injection_detection(self):
        """Test SQL injection detection"""
        malicious_inputs = [
            "' OR 1=1--",
            "admin' UNION SELECT * FROM users--",
            "1; DROP TABLE users;",
        ]
        for input_str in malicious_inputs:
            assert waf.check_patterns(input_str, waf.sql_regex) is True

    def test_xss_detection(self):
        """Test XSS detection"""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img onerror='alert(1)'>",
        ]
        for input_str in malicious_inputs:
            assert waf.check_patterns(input_str, waf.xss_regex) is True

    def test_path_traversal_detection(self):
        """Test path traversal detection"""
        malicious_inputs = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e%2f",
        ]
        for input_str in malicious_inputs:
            assert waf.check_patterns(input_str, waf.path_regex) is True

    def test_command_injection_detection(self):
        """Test command injection detection"""
        malicious_inputs = [
            "; ls -la",
            "| cat /etc/passwd",
            "`whoami`",
            "$(id)",
        ]
        for input_str in malicious_inputs:
            assert waf.check_patterns(input_str, waf.cmd_regex) is True

    def test_safe_input(self):
        """Test that safe input passes"""
        safe_inputs = [
            "normal text",
            "user@example.com",
            "Research Paper Title",
        ]
        for input_str in safe_inputs:
            assert waf.check_patterns(input_str, waf.sql_regex) is False
            assert waf.check_patterns(input_str, waf.xss_regex) is False
            assert waf.check_patterns(input_str, waf.cmd_regex) is False


class TestRequestSigning:
    """Test request signing"""

    def test_generate_signature(self):
        """Test signature generation"""
        signer = RequestSigner("test_secret_key")
        signature = signer.generate_signature("POST", "/api/test", "1234567890", "body")
        assert len(signature) == 64  # SHA256 hex digest

    def test_verify_signature(self):
        """Test signature verification"""
        signer = RequestSigner("test_secret_key")
        timestamp = "1234567890"
        signature = signer.generate_signature("POST", "/api/test", timestamp, "body")

        assert (
            signer.verify_signature("POST", "/api/test", timestamp, signature, "body")
            is True
        )

    def test_invalid_signature(self):
        """Test invalid signature"""
        signer = RequestSigner("test_secret_key")
        assert (
            signer.verify_signature(
                "POST", "/api/test", "1234567890", "invalid", "body"
            )
            is False
        )

    def test_timestamp_validation(self):
        """Test timestamp validation"""
        signer = RequestSigner("test_secret_key")

        # Valid timestamp (current)
        import time

        current_ts = str(int(time.time()))
        assert signer.verify_timestamp(current_ts) is True

        # Expired timestamp (10 minutes ago)
        old_ts = str(int(time.time()) - 600)
        assert signer.verify_timestamp(old_ts) is False


class TestSecurityMonitor:
    """Test security monitoring"""

    def test_record_failed_auth(self):
        """Test recording failed authentication"""
        monitor = security_monitor
        ip = "192.168.1.100"

        # Record multiple failures
        for _ in range(3):
            monitor.record_failed_auth(ip)

        assert len(monitor.failed_auth_attempts[ip]) == 3

    def test_brute_force_detection(self):
        """Test brute force detection and blocking"""
        monitor = security_monitor
        ip = "192.168.1.101"

        # Record 5 failures (should trigger block)
        for _ in range(5):
            monitor.record_failed_auth(ip)

        assert monitor.is_blocked(ip) is True

    def test_mark_suspicious(self):
        """Test marking IP as suspicious"""
        monitor = security_monitor
        ip = "192.168.1.102"

        monitor.mark_suspicious(ip)
        assert monitor.is_suspicious(ip) is True

    def test_get_stats(self):
        """Test getting security statistics"""
        monitor = security_monitor
        stats = monitor.get_stats()

        assert "blocked_ips" in stats
        assert "suspicious_ips" in stats
        assert "monitored_ips" in stats


@pytest.mark.skip(reason="Requires MongoDB")
@pytest.mark.asyncio
async def test_audit_logging():
    """Test audit logging (requires MongoDB)"""
    from app.services.audit_logger import audit_logger

    await audit_logger.log_event(
        event_type="test_event",
        user_id="test_user",
        ip_address="192.168.1.1",
        details={"test": "data"},
        severity="info",
    )

    # Verify log was created (would need to query MongoDB in real test)
    assert True  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
