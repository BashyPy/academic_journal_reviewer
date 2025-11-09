"""WebAuthn passkey service for biometric authentication"""

import base64
import secrets
from typing import Optional

from app.services.mongodb_service import mongodb_service
from app.utils.logger import get_logger

logger = get_logger(__name__)

DB_CONNECTION_ERROR = "Database connection not available"


class WebAuthnService:
    """Service for WebAuthn passkey operations"""

    async def generate_registration_options(self, user_email: str, user_id: str) -> dict:
        """Generate options for passkey registration"""
        if not user_email or not isinstance(user_email, str):
            raise ValueError("Valid user_email is required")

        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

        db = await mongodb_service.get_database()
        if not db:
            raise RuntimeError(DB_CONNECTION_ERROR)

        try:
            await db["webauthn_challenges"].insert_one(
                {
                    "user_email": user_email,
                    "challenge": challenge_b64,
                    "type": "registration",
                    "used": False,
                }
            )
        except Exception as e:
            logger.error(f"Failed to insert webauthn challenge for {user_email}: {e}")
            raise RuntimeError("Failed to save challenge to database") from e

        return {
            "challenge": challenge_b64,
            "rp": {"name": "AARIS", "id": "localhost"},
            "user": {
                "id": base64.urlsafe_b64encode(user_id.encode()).decode("utf-8").rstrip("="),
                "name": user_email,
                "displayName": user_email,
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},  # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "timeout": 60000,
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "requireResidentKey": True,
                "residentKey": "required",
                "userVerification": "required",
            },
        }

    async def verify_registration(self, user_email: str, credential: dict) -> bool:
        """Verify and store passkey registration"""
        db = await mongodb_service.get_database()
        if not db:
            raise RuntimeError(DB_CONNECTION_ERROR)

        try:
            challenge_doc = await db["webauthn_challenges"].find_one(
                {"user_email": user_email, "type": "registration", "used": False}
            )

            if not challenge_doc:
                logger.warning(
                    f"Registration verification failed for {user_email}: challenge not found or already used."
                )
                return False

            await db["webauthn_challenges"].update_one(
                {"_id": challenge_doc["_id"]}, {"$set": {"used": True}}
            )

            await db["passkeys"].insert_one(
                {
                    "user_email": user_email,
                    "credential_id": credential["id"],
                    "public_key": credential["response"]["publicKey"],
                    "counter": credential["response"].get("counter", 0),
                    "transports": credential["response"].get("transports", []),
                }
            )

            logger.info(f"Passkey registered for {user_email}")
            return True
        except Exception as e:
            logger.error(f"Error during passkey registration for {user_email}: {e}")
            return False

    async def generate_authentication_options(self, user_email: Optional[str] = None) -> dict:
        """Generate options for passkey authentication"""
        challenge = secrets.token_bytes(32)
        challenge_b64 = base64.urlsafe_b64encode(challenge).decode("utf-8").rstrip("=")

        db = await mongodb_service.get_database()
        if not db:
            raise RuntimeError("Database connection not available")

        try:
            await db["webauthn_challenges"].insert_one(
                {
                    "user_email": user_email,
                    "challenge": challenge_b64,
                    "type": "authentication",
                    "used": False,
                }
            )
        except Exception as e:
            logger.error(f"Failed to insert webauthn challenge for {user_email}: {e}")
            raise RuntimeError("Failed to save challenge to database") from e

        options = {
            "challenge": challenge_b64,
            "timeout": 60000,
            "rpId": "localhost",
            "userVerification": "required",
        }

        if user_email:
            try:
                passkeys = await db["passkeys"].find({"user_email": user_email}).to_list(None)
                if passkeys:
                    options["allowCredentials"] = [
                        {
                            "type": "public-key",
                            "id": pk["credential_id"],
                            "transports": pk.get("transports", ["internal"]),
                        }
                        for pk in passkeys
                    ]
            except Exception as e:
                logger.error(f"Failed to retrieve passkeys for {user_email}: {e}")
                # Continue without allowCredentials if passkey retrieval fails
        return options

    async def verify_authentication(self, credential: dict) -> Optional[str]:
        """Verify passkey authentication and return user email"""
        db = await mongodb_service.get_database()
        if not db:
            logger.error("Database connection not available for authentication verification")
            return None

        try:
            passkey = await db["passkeys"].find_one({"credential_id": credential["id"]})
            if not passkey:
                logger.warning(
                    f"Authentication failed: passkey not found for credential ID {credential['id']}"
                )
                return None

            challenge_doc = await db["webauthn_challenges"].find_one(
                {"user_email": passkey["user_email"], "type": "authentication", "used": False}
            )

            if not challenge_doc:
                logger.warning(
                    f"Authentication failed for {passkey['user_email']}: challenge not found or already used."
                )
                return None

            await db["webauthn_challenges"].update_one(
                {"_id": challenge_doc["_id"]}, {"$set": {"used": True}}
            )

            await db["passkeys"].update_one(
                {"_id": passkey["_id"]},
                {"$set": {"counter": credential["response"].get("counter", passkey["counter"])}},
            )

            logger.info(f"Passkey authentication successful for {passkey['user_email']}")
            return passkey["user_email"]
        except Exception as e:
            logger.error(f"Error during passkey authentication: {e}")
            return None

    async def list_passkeys(self, user_email: str) -> list:
        """List all passkeys for a user"""
        db = await mongodb_service.get_database()
        passkeys = await db["passkeys"].find({"user_email": user_email}).to_list(None)
        return [
            {"id": pk["credential_id"], "transports": pk.get("transports", [])} for pk in passkeys
        ]

    async def delete_passkey(self, user_email: str, credential_id: str) -> bool:
        """Delete a specific passkey"""
        db = await mongodb_service.get_database()
        result = await db["passkeys"].delete_one(
            {"user_email": user_email, "credential_id": credential_id}
        )
        return result.deleted_count > 0


webauthn_service = WebAuthnService()
