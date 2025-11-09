"""User management service"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from pymongo.errors import PyMongoError

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger
from app.utils.validators import validate_password, validate_username

logger = get_logger(__name__)


MONGO_UNSET = "$unset"


class UserService:
    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize users collection"""
        if self.collection is None:
            db = mongodb_service.get_database()
            self.collection = db["users"]
            await self.collection.create_index("email", unique=True)
            await self.collection.create_index("username", unique=True, sparse=True)
            await self.collection.create_index("api_key", unique=True)

    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
        return "$".join([salt, pwd_hash.hex()])

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split("$")
            new_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
            return new_hash.hex() == pwd_hash
        except (ValueError, TypeError):
            return False

    def generate_api_key(self) -> str:
        """Generate API key"""
        return f"aaris_{secrets.token_urlsafe(32)}"

    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: str = "author",
        username: Optional[str] = None,
    ) -> dict:
        """Create new user"""
        try:
            await self.initialize()
            if self.collection is None:
                raise RuntimeError("User collection is not initialized.")
            self._validate_role(role)
            self._validate_password_strength(password)
            self._validate_username_format(username)

            await self._check_email_uniqueness(email)
            if username:
                await self._check_username_uniqueness(username)

            api_key = self.generate_api_key()
            user = {
                "email": email,
                "password": self.hash_password(password),
                "name": name,
                "role": role,
                "api_key": api_key,
                "email_verified": False,
                "is_active": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            if username:
                user["username"] = username

            result = await self.collection.insert_one(user)
            user["_id"] = str(result.inserted_id)
            logger.info(f"User created: {email}")
            return user
        except ValueError as e:
            logger.warning(f"Validation error during user creation for {email}: {e}")
            raise
        except PyMongoError as e:
            logger.error(e, additional_info={"email": email, "function": "create_user"})
            raise ValueError("Could not create user due to a database error.") from e

    def _validate_role(self, role: str):
        allowed_roles = {"author", "reviewer", "editor", "admin"}
        if not role or role not in allowed_roles:
            raise ValueError(f"Invalid role: {role}. Allowed roles are: {', '.join(allowed_roles)}")

    def _validate_password_strength(self, password: str):
        is_valid, msg = validate_password(password)
        if not is_valid:
            raise ValueError(msg)

    def _validate_username_format(self, username: Optional[str]):
        if username is not None:
            if not isinstance(username, str) or not username.strip():
                raise ValueError("Username must be a non-empty string if provided")
            is_valid, msg = validate_username(username)
            if not is_valid:
                raise ValueError(msg)

    async def _check_email_uniqueness(self, email: str):
        existing = await self.collection.find_one({"email": email})
        if existing:
            raise ValueError("Email already registered")

    async def _check_username_uniqueness(self, username: str):
        existing_username = await self.collection.find_one({"username": username})
        if existing_username:
            raise ValueError("Username already taken")

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        await self.initialize()
        return await self.collection.find_one({"email": email})

    async def get_user_by_api_key(self, api_key: str) -> Optional[dict]:
        """Get user by API key"""
        await self.initialize()
        user = await self.collection.find_one({"api_key": api_key, "is_active": True})
        if user:
            user["name"] = user.get("name", user["email"])
        return user

    async def verify_email(self, email: str) -> bool:
        """Mark email as verified, activate account, and clear OTP"""
        await self.initialize()
        result = await self.collection.update_one(
            {"email": email},
            {
                "$set": {
                    "email_verified": True,
                    "is_active": True,
                    "updated_at": datetime.now(),
                },
                MONGO_UNSET: {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
            },
        )
        return result.modified_count > 0

    async def update_password(self, email: str, new_password: str) -> bool:
        """Update user password and clear OTP"""
        await self.initialize()

        # Validate password strength
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            raise ValueError(msg)
        try:
            result = await self.collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "password": self.hash_password(new_password),
                        "updated_at": datetime.now(),
                    },
                    MONGO_UNSET: {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
                },
            )
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(e, additional_info={"email": email, "function": "update_password"})
            return False

    async def update_profile(self, email: str, profile_data: dict) -> bool:
        """Update user profile"""
        if not email or not isinstance(email, str):
            raise ValueError("Valid email is required")
        if not isinstance(profile_data, dict):
            raise ValueError("Profile data must be a dictionary")

        await self.initialize()

        update_data = {}
        allowed_fields = ["name", "username"]
        for field in allowed_fields:
            if field in profile_data:
                update_data[field] = profile_data[field]

        if not update_data:
            return True  # No fields to update

        if "username" in update_data:
            is_valid, msg = validate_username(update_data["username"])
            if not is_valid:
                raise ValueError(msg)
            existing_user = await self.collection.find_one(
                {"username": update_data["username"], "email": {"$ne": email}}
            )
            if existing_user:
                raise ValueError("Username already taken")

        update_data["updated_at"] = datetime.now()

        try:
            result = await self.collection.update_one({"email": email}, {"$set": update_data})
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(e, additional_info={"email": email, "function": "update_profile"})
            return False

    async def delete_user(self, email: str) -> bool:
        """Delete user account"""
        await self.initialize()
        try:
            result = await self.collection.delete_one({"email": email})
            logger.info(f"User deleted: {email}")
            return result.deleted_count > 0
        except PyMongoError as e:
            logger.error(e, additional_info={"email": email, "function": "delete_user"})
            return False

    async def change_email(self, old_email: str, new_email: str) -> bool:
        """Change user email and clear OTP"""
        await self.initialize()
        try:
            result = await self.collection.update_one(
                {"email": old_email},
                {
                    "$set": {
                        "email": new_email,
                        "pending_email": None,
                        "updated_at": datetime.now(),
                    },
                    MONGO_UNSET: {"otp": "", "otp_purpose": "", "otp_expires_at": ""},
                },
            )
            logger.info(f"Email changed: {old_email} -> {new_email}")
            return result.modified_count > 0
        except PyMongoError as e:
            logger.error(
                e,
                additional_info={
                    "old_email": old_email,
                    "new_email": new_email,
                    "function": "change_email",
                },
            )
            return False

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user by username"""
        await self.initialize()
        try:
            return await self.collection.find_one({"username": username})
        except PyMongoError as e:
            logger.error(
                e, additional_info={"username": username, "function": "get_user_by_username"}
            )
            return None

    async def authenticate(self, email_or_username: str, password: str) -> Optional[dict]:
        """Authenticate user by email or username"""
        user = await self.get_user_by_email(email_or_username)
        if not user:
            user = await self.get_user_by_username(email_or_username)

        if user and self.verify_password(password, user["password"]):
            if not user.get("is_active", True):
                return None
            return user
        return None


user_service = UserService()
