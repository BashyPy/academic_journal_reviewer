import os
import re
from typing import Optional

from dotenv import load_dotenv

from app.utils.logger import get_logger

load_dotenv()


logger = get_logger(__name__)


class Settings:  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    def __init__(self):
        # Secure configuration loading with validation
        # Use the centralized default constant
        self.MONGODB_URL = self._validate_mongodb_url(
            os.getenv("MONGODB_URL")
        )  # pylint: disable=invalid-name
        # Use test database when running tests (override .env setting)
        if os.getenv("TESTING") == "true":
            self.MONGODB_DATABASE = self._validate_database_name(
                "aaris_test"
            )  # pylint: disable=invalid-name
        else:
            self.MONGODB_DATABASE = self._validate_database_name(  # pylint: disable=invalid-name
                os.getenv("MONGODB_DATABASE", "aaris")
            )

        try:
            self.DEFAULT_LLM = self._validate_llm_provider(
                os.getenv("DEFAULT_LLM", "groq")
            )  # pylint: disable=invalid-name
            self.GROQ_API_KEY = self._validate_api_key(
                os.getenv("GROQ_API_KEY")
            )  # pylint: disable=invalid-name
            self.OPENAI_API_KEY = self._validate_api_key(
                os.getenv("OPENAI_API_KEY")
            )  # pylint: disable=invalid-name
            self.GEMINI_API_KEY = self._validate_api_key(
                os.getenv("GEMINI_API_KEY")
            )  # pylint: disable=invalid-name
            self.ANTHROPIC_API_KEY = self._validate_api_key(
                os.getenv("ANTHROPIC_API_KEY")
            )  # pylint: disable=invalid-name

            self.APP_ID = self._validate_app_id(
                os.getenv("APP_ID", "aaris-app")
            )  # pylint: disable=invalid-name
            jwt_secret = os.getenv(
                "JWT_SECRET", "change-this-secret-in-production-use-strong-random-key"
            )
            if len(jwt_secret) < 32:
                logger.warning(
                    "JWT_SECRET is too short. Use at least 32 characters for production."
                )
            if jwt_secret == "change-this-secret-in-production-use-strong-random-key":
                logger.warning("Using default JWT_SECRET. Change this in production!")
            self.JWT_SECRET = jwt_secret  # pylint: disable=invalid-name
        except (ValueError, TypeError) as e:
            logger.error("Error processing environment variables: %s", e)
            # Set safe defaults or re-raise as appropriate
            self.DEFAULT_LLM = "groq"
            self.GROQ_API_KEY = None
            self.OPENAI_API_KEY = None
            self.GEMINI_API_KEY = None
            self.ANTHROPIC_API_KEY = None
            self.APP_ID = "aaris-app"
            self.JWT_SECRET = "change-this-secret-in-production-use-strong-random-key"

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
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Unexpected error validating MONGODB_URL, using default URI.")
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
            logger.exception("Regex error validating MONGODB_DATABASE, falling back to 'aaris'.")
            return "aaris"
        except Exception:  # pylint: disable=broad-exception-caught
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
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Unexpected error validating DEFAULT_LLM, falling back to 'groq'.")
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
        except Exception:  # pylint: disable=broad-exception-caught
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
        except re.error as e:
            logger.error("Regex error validating APP_ID: %s. Falling back to 'aaris-app'.", e)
            return "aaris-app"
        except TypeError as e:
            logger.error("Type error validating APP_ID: %s. Falling back to 'aaris-app'.", e)
            return "aaris-app"

    def get_jwt_secret(self) -> str:
        """Get JWT secret with warning if using default"""
        if self.JWT_SECRET == "change-this-secret-in-production-use-strong-random-key":
            logger.warning("Using default JWT_SECRET. Set JWT_SECRET in .env for production!")
        return self.JWT_SECRET


settings = Settings()
