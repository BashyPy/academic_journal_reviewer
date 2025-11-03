"""User management service"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger
from app.utils.validators import validate_password, validate_username

logger = get_logger(__name__)


class UserService:
    def __init__(self):
        self.collection = None

    async def initialize(self):
        """Initialize users collection"""
        if self.collection is None:
            db = await mongodb_service.get_database()
            self.collection = db["users"]
            await self.collection.create_index("email", unique=True)
            await self.collection.create_index("username", unique=True, sparse=True)
            await self.collection.create_index("api_key", unique=True)

    def hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        )
        return f"{salt}${pwd_hash.hex()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            salt, pwd_hash = hashed.split("$")
            new_hash = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), salt.encode(), 100000
            )
            return new_hash.hex() == pwd_hash
        except Exception:
            return False

    def generate_api_key(self) -> str:
        """Generate API key"""
        return f"aaris_{secrets.token_urlsafe(32)}"

    async def create_user(
        self, email: str, password: str, name: str, role: str = "author", username: str = None
    ) -> dict:
        """Create new user"""
        await self.initialize()

        # Validate password strength
        is_valid, msg = validate_password(password)
        if not is_valid:
            raise ValueError(msg)
        
        # Validate username format
        if username:
            is_valid, msg = validate_username(username)
            if not is_valid:
                raise ValueError(msg)

        # Check email uniqueness
        existing = await self.collection.find_one({"email": email})
        if existing:
            raise ValueError("Email already registered")
        
        # Check username uniqueness
        if username:
            existing_username = await self.collection.find_one({"username": username})
            if existing_username:
                raise ValueError("Username already taken")

        api_key = self.generate_api_key()
        user = {
            "email": email,
            "password": self.hash_password(password),
            "name": name,
            "role": role,
            "api_key": api_key,
            "email_verified": False,
            "active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        
        if username:
            user["username"] = username

        result = await self.collection.insert_one(user)
        user["_id"] = str(result.inserted_id)
        logger.info(f"User created: {email}")
        return user

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email"""
        await self.initialize()
        return await self.collection.find_one({"email": email})

    async def get_user_by_api_key(self, api_key: str) -> Optional[dict]:
        """Get user by API key"""
        await self.initialize()
        user = await self.collection.find_one({"api_key": api_key, "active": True})
        if user:
            user["name"] = user.get("name", user["email"])
        return user

    async def verify_email(self, email: str) -> bool:
        """Mark email as verified"""
        await self.initialize()
        result = await self.collection.update_one(
            {"email": email},
            {"$set": {"email_verified": True, "updated_at": datetime.now()}},
        )
        return result.modified_count > 0

    async def update_password(self, email: str, new_password: str) -> bool:
        """Update user password"""
        await self.initialize()
        
        # Validate password strength
        is_valid, msg = validate_password(new_password)
        if not is_valid:
            raise ValueError(msg)
        
        result = await self.collection.update_one(
            {"email": email},
            {
                "$set": {
                    "password": self.hash_password(new_password),
                    "updated_at": datetime.now(),
                }
            },
        )
        return result.modified_count > 0

    async def update_profile(self, email: str, profile_data: dict) -> bool:
        """Update user profile"""
        await self.initialize()
        profile_data["updated_at"] = datetime.now()
        result = await self.collection.update_one(
            {"email": email}, {"$set": profile_data}
        )
        return result.modified_count > 0

    async def delete_user(self, email: str) -> bool:
        """Delete user account"""
        await self.initialize()
        result = await self.collection.delete_one({"email": email})
        logger.info(f"User deleted: {email}")
        return result.deleted_count > 0

    async def change_email(self, old_email: str, new_email: str) -> bool:
        """Change user email"""
        await self.initialize()
        result = await self.collection.update_one(
            {"email": old_email},
            {"$set": {"email": new_email, "pending_email": None, "updated_at": datetime.now()}}
        )
        logger.info(f"Email changed: {old_email} -> {new_email}")
        return result.modified_count > 0

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user by username"""
        await self.initialize()
        return await self.collection.find_one({"username": username})

    async def authenticate(self, email_or_username: str, password: str) -> Optional[dict]:
        """Authenticate user by email or username"""
        user = await self.get_user_by_email(email_or_username)
        if not user:
            user = await self.get_user_by_username(email_or_username)
        
        if user and self.verify_password(password, user["password"]):
            if not user.get("active", True):
                return None
            return user
        return None


user_service = UserService()
