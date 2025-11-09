"""Initialize default super admin user"""

import asyncio
import base64
import binascii
import os

from dotenv import load_dotenv

from app.services.user_service import user_service
from app.utils.logger import get_logger

# Load environment variables first
load_dotenv()

logger = get_logger(__name__)

DEFAULT_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
_raw_password = os.getenv("SUPER_ADMIN_PASSWORD")
try:
    DEFAULT_ADMIN_PASSWORD = (
        base64.b64decode(_raw_password).decode("utf-8") if _raw_password else None
    )
except (binascii.Error, UnicodeDecodeError):
    DEFAULT_ADMIN_PASSWORD = _raw_password
DEFAULT_ADMIN_USERNAME = os.getenv("SUPER_ADMIN_USERNAME")
DEFAULT_ADMIN_NAME = os.getenv("SUPER_ADMIN_NAME")


async def _handle_existing_admin(email):
    """Handle logic for an existing admin user."""
    existing = await user_service.get_user_by_email(email)
    if not existing:
        return None

    logger.info(f"Admin user already exists: {email}")
    if not existing.get("is_active") or not existing.get("email_verified"):
        await user_service.verify_email(email)
        logger.info(f"✅ Admin user activated and verified: {email}")
    return existing


async def create_default_admin():
    """Create default super admin if not exists"""
    try:
        if not all(
            [
                DEFAULT_ADMIN_EMAIL,
                DEFAULT_ADMIN_PASSWORD,
                DEFAULT_ADMIN_USERNAME,
                DEFAULT_ADMIN_NAME,
            ]
        ):
            error_message = (
                "One or more super admin environment variables are not set. "
                "Please check SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD, "
                "SUPER_ADMIN_USERNAME, SUPER_ADMIN_NAME."
            )
            logger.error(error_message)
            raise ValueError(error_message)

        # Type assertions to satisfy the type checker
        assert DEFAULT_ADMIN_EMAIL is not None
        assert DEFAULT_ADMIN_PASSWORD is not None
        assert DEFAULT_ADMIN_USERNAME is not None
        assert DEFAULT_ADMIN_NAME is not None

        logger.info(f"Checking for admin user: {DEFAULT_ADMIN_EMAIL}")
        if existing_admin := await _handle_existing_admin(DEFAULT_ADMIN_EMAIL):
            return existing_admin

        logger.info(f"Creating new admin user: {DEFAULT_ADMIN_EMAIL}")
        admin = await user_service.create_user(
            email=DEFAULT_ADMIN_EMAIL,
            password=DEFAULT_ADMIN_PASSWORD,
            name=DEFAULT_ADMIN_NAME,
            role="super_admin",
            username=DEFAULT_ADMIN_USERNAME,
        )
        await user_service.verify_email(DEFAULT_ADMIN_EMAIL)
        logger.info(f"✅ Default admin created and activated: {DEFAULT_ADMIN_EMAIL}")
        logger.info(f"🔑 Username: {DEFAULT_ADMIN_USERNAME}")
        return admin

    except Exception as e:
        if "E11000 duplicate key error" in str(e) and DEFAULT_ADMIN_EMAIL:
            logger.info(f"Admin user already exists (duplicate key): {DEFAULT_ADMIN_EMAIL}")
            return await _handle_existing_admin(DEFAULT_ADMIN_EMAIL)

        logger.error(f"❌ Failed to create default admin: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    asyncio.run(create_default_admin())
