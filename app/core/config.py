import logging
import os
import re
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


logger = logging.getLogger(__name__)


class Settings:
    def __init__(self):
        # Secure configuration loading with validation
        # Use the centralized default constant
        self.MONGODB_URL = self._validate_mongodb_url(os.getenv("MONGODB_URL"))
        self.MONGODB_DATABASE = self._validate_database_name(
            os.getenv("MONGODB_DATABASE", "aaris")
        )

        self.DEFAULT_LLM = self._validate_llm_provider(os.getenv("DEFAULT_LLM", "groq"))
        self.GROQ_API_KEY = self._validate_api_key(os.getenv("GROQ_API_KEY"))
        self.OPENAI_API_KEY = self._validate_api_key(os.getenv("OPENAI_API_KEY"))
        self.GEMINI_API_KEY = self._validate_api_key(os.getenv("GEMINI_API_KEY"))
        self.ANTHROPIC_API_KEY = self._validate_api_key(os.getenv("ANTHROPIC_API_KEY"))

        self.APP_ID = self._validate_app_id(os.getenv("APP_ID", "aaris-app"))

    def _validate_mongodb_url(self, url: Optional[str]) -> str:
        """Validate MongoDB URL format with defensive error handling"""
        try:
            if not url:
                return ""

            # Basic URL validation to prevent injection
            if not url.startswith(("mongodb://", "mongodb+srv://")):
                logger.warning("Invalid MONGODB_URL prefix, falling back to default.")
                return ""

            # Remove any dangerous characters
            safe_url = re.sub(r'[<>"\\]', "", url)
            return safe_url
        except re.error:
            logger.exception("Regex error validating MONGODB_URL, using default URI.")
            return ""
        except Exception:
            logger.exception(
                "Unexpected error validating MONGODB_URL, using default URI."
            )
            return ""

    def _validate_database_name(self, name: Optional[str]) -> str:
        """Validate database name with defensive error handling"""
        try:
            if not name:
                return "aaris"

            # Only allow alphanumeric, underscore, and hyphen
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
            if not safe_name or len(safe_name) > 64:
                logger.warning("Invalid MONGODB_DATABASE, falling back to 'aaris'.")
                return "aaris"

            return safe_name
        except re.error:
            logger.exception(
                "Regex error validating MONGODB_DATABASE, falling back to 'aaris'."
            )
            return "aaris"
        except Exception:
            logger.exception(
                "Unexpected error validating MONGODB_DATABASE, falling back to 'aaris'."
            )
            return "aaris"

    def _validate_llm_provider(self, provider: Optional[str]) -> str:
        """Validate LLM provider"""
        try:
            valid_providers = {"openai", "anthropic", "gemini", "groq"}
            if provider and provider.lower() in valid_providers:
                return provider.lower()
        except Exception:
            logger.exception(
                "Unexpected error validating DEFAULT_LLM, falling back to 'groq'."
            )
        return "groq"

    def _validate_api_key(self, key: Optional[str]) -> Optional[str]:
        """Validate API key format with defensive error handling"""
        try:
            if not key or not isinstance(key, str):
                return None

            # Basic API key validation (remove dangerous characters)
            safe_key = re.sub(r'[<>"\\\n\r\t]', "", key.strip())

            # Check minimum length
            if len(safe_key) < 10:
                return None

            return safe_key
        except re.error:
            logger.exception("Regex error validating API key, dropping key.")
            return None
        except Exception:
            logger.exception("Unexpected error validating API key, dropping key.")
            return None

    def _validate_app_id(self, app_id: Optional[str]) -> str:
        """Validate application ID with defensive error handling"""
        try:
            if not app_id:
                return "aaris-app"

            # Only allow alphanumeric, underscore, and hyphen
            safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", app_id)
            if not safe_id or len(safe_id) > 32:
                logger.warning("Invalid APP_ID, falling back to 'aaris-app'.")
                return "aaris-app"

            return safe_id
        except re.error:
            logger.exception(
                "Regex error validating APP_ID, falling back to 'aaris-app'."
            )
            return "aaris-app"
        except Exception:
            logger.exception(
                "Unexpected error validating APP_ID, falling back to 'aaris-app'."
            )
            return "aaris-app"


settings = Settings()
