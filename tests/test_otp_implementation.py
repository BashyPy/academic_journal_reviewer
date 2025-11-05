#!/usr/bin/env python3
"""Test script for the new OTP implementation"""

import asyncio
from datetime import datetime, timedelta

from app.services.mongodb_service import mongodb_service
from app.services.otp_cleanup_service import otp_cleanup_service
from app.services.otp_service import otp_service
from app.services.user_service import user_service


async def test_otp_implementation():
    """Test the new OTP implementation"""
    print("Testing OTP implementation...")

    # Initialize services
    await mongodb_service.initialize()

    # Test user email
    test_email = "test@example.com"

    try:
        # 1. Create a test user
        print("1. Creating test user...")
        user = await user_service.create_user(
            email=test_email, password="TestPass123!", name="Test User"
        )
        print(f"✓ User created: {user['email']}")

        # 2. Create OTP
        print("2. Creating OTP...")
        otp = await otp_service.create_otp(test_email, "email_verification")
        print(f"✓ OTP created: {otp}")

        # 3. Verify user has OTP in their record
        print("3. Checking OTP storage...")
        user_data = await user_service.get_user_by_email(test_email)
        assert user_data.get("otp") == otp
        assert user_data.get("otp_purpose") == "email_verification"
        assert user_data.get("otp_expires_at") is not None
        print("✓ OTP stored in user record")

        # 4. Verify OTP
        print("4. Verifying OTP...")
        is_valid = await otp_service.verify_otp(test_email, otp, "email_verification")
        assert is_valid
        print("✓ OTP verification successful")

        # 5. Complete email verification (should clear OTP)
        print("5. Completing email verification...")
        await user_service.verify_email(test_email)
        user_data = await user_service.get_user_by_email(test_email)
        assert "otp" not in user_data
        assert "otp_purpose" not in user_data
        assert "otp_expires_at" not in user_data
        assert user_data.get("email_verified") is True
        print("✓ Email verified and OTP cleared")

        # 6. Test password reset OTP
        print("6. Testing password reset OTP...")
        reset_otp = await otp_service.create_otp(test_email, "password_reset")
        user_data = await user_service.get_user_by_email(test_email)
        assert user_data.get("otp") == reset_otp
        assert user_data.get("otp_purpose") == "password_reset"
        print("✓ Password reset OTP created")

        # 7. Reset password (should clear OTP)
        print("7. Resetting password...")
        is_valid = await otp_service.verify_otp(test_email, reset_otp, "password_reset")
        assert is_valid
        await user_service.update_password(test_email, "NewPass123!")
        user_data = await user_service.get_user_by_email(test_email)
        assert "otp" not in user_data
        print("✓ Password reset and OTP cleared")

        # 8. Test expired OTP cleanup
        print("8. Testing expired OTP cleanup...")
        await otp_service.create_otp(test_email, "test_cleanup")

        # Manually set expiration to past
        db = await mongodb_service.get_database()
        users_collection = db["users"]
        await users_collection.update_one(
            {"email": test_email},
            {"$set": {"otp_expires_at": datetime.now() - timedelta(minutes=1)}},
        )

        # Run cleanup
        cleaned_count = await otp_cleanup_service.cleanup_expired_otps()
        assert cleaned_count >= 1

        # Verify OTP was cleared
        user_data = await user_service.get_user_by_email(test_email)
        assert "otp" not in user_data
        print("✓ Expired OTP cleanup successful")

        print("\n🎉 All tests passed! OTP implementation is working correctly.")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Cleanup test user
        try:
            await user_service.delete_user(test_email)
            print("✓ Test user cleaned up")
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(test_otp_implementation())
