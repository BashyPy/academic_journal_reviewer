"""Tests for authentication system"""

import pytest

from app.services.otp_service import otp_service
from app.services.user_service import user_service


class TestUserService:
    """Test user service"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "TestPassword123"
        hashed = user_service.hash_password(password)

        assert "$" in hashed
        assert len(hashed) > 50
        assert user_service.verify_password(password, hashed)
        assert not user_service.verify_password("WrongPassword", hashed)

    def test_generate_api_key(self):
        """Test API key generation"""
        key = user_service.generate_api_key()

        assert key.startswith("aaris_")
        assert len(key) > 40


class TestOTPService:
    """Test OTP service"""

    def test_generate_otp(self):
        """Test OTP generation"""
        otp = otp_service.generate_otp()

        assert len(otp) == 6
        assert otp.isdigit()


@pytest.mark.skip(reason="Requires MongoDB")
class TestAuthenticationFlow:
    """Test complete authentication flow (requires MongoDB)"""

    @pytest.mark.asyncio
    async def test_user_registration(self):
        """Test user registration"""
        user = await user_service.create_user(
            email="test@example.com", password="TestPass123", name="Test User"
        )

        assert user["email"] == "test@example.com"
        assert user["name"] == "Test User"
        assert user["role"] == "user"
        assert "api_key" in user
        assert user["email_verified"] is False

    @pytest.mark.asyncio
    async def test_email_verification(self):
        """Test email verification"""
        email = "verify@example.com"

        await user_service.create_user(email, "Pass123", "Test")
        otp = await otp_service.create_otp(email, "email_verification")

        assert await otp_service.verify_otp(email, otp, "email_verification")
        assert await user_service.verify_email(email)

    @pytest.mark.asyncio
    async def test_authentication(self):
        """Test user authentication"""
        email = "auth@example.com"
        password = "AuthPass123"

        await user_service.create_user(email, password, "Auth User")
        await user_service.verify_email(email)

        user = await user_service.authenticate(email, password)
        assert user is not None
        assert user["email"] == email

    @pytest.mark.asyncio
    async def test_password_reset(self):
        """Test password reset"""
        email = "reset@example.com"
        old_pass = "OldPass123"
        new_pass = "NewPass123"

        await user_service.create_user(email, old_pass, "Reset User")
        otp = await otp_service.create_otp(email, "password_reset")

        assert await otp_service.verify_otp(email, otp, "password_reset")
        assert await user_service.update_password(email, new_pass)

        user = await user_service.authenticate(email, new_pass)
        assert user is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
