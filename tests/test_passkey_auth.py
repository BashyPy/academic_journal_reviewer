"""Tests for passkey authentication"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.webauthn_service import webauthn_service


@pytest.mark.asyncio
async def test_generate_registration_options():
    """Test generating WebAuthn registration options"""
    with patch.object(webauthn_service, 'generate_registration_options', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "challenge": "test_challenge",
            "rp": {"name": "AARIS", "id": "localhost"},
            "user": {
                "id": "test_user_id",
                "name": "test@example.com",
                "displayName": "test@example.com"
            }
        }

        options = await webauthn_service.generate_registration_options("test@example.com", "user123")

        assert options["challenge"] == "test_challenge"
        assert options["rp"]["name"] == "AARIS"
        assert options["user"]["name"] == "test@example.com"


@pytest.mark.asyncio
async def test_verify_registration():
    """Test verifying passkey registration"""
    with patch.object(webauthn_service, 'verify_registration', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = True

        credential = {
            "id": "test_credential_id",
            "response": {
                "publicKey": "test_public_key",
                "counter": 0,
                "transports": ["internal"]
            }
        }

        result = await webauthn_service.verify_registration("test@example.com", credential)

        assert result is True


@pytest.mark.asyncio
async def test_generate_authentication_options():
    """Test generating WebAuthn authentication options"""
    with patch.object(webauthn_service, 'generate_authentication_options', new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "challenge": "auth_challenge",
            "timeout": 60000,
            "rpId": "localhost",
            "userVerification": "required"
        }

        options = await webauthn_service.generate_authentication_options("test@example.com")

        assert options["challenge"] == "auth_challenge"
        assert options["userVerification"] == "required"


@pytest.mark.asyncio
async def test_verify_authentication():
    """Test verifying passkey authentication"""
    with patch.object(webauthn_service, 'verify_authentication', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = "test@example.com"

        credential = {
            "id": "test_credential_id",
            "response": {
                "authenticatorData": "test_data",
                "signature": "test_signature",
                "counter": 1
            }
        }

        user_email = await webauthn_service.verify_authentication(credential)

        assert user_email == "test@example.com"


@pytest.mark.asyncio
async def test_list_passkeys():
    """Test listing user passkeys"""
    with patch.object(webauthn_service, 'list_passkeys', new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            {"id": "credential1", "transports": ["internal"]},
            {"id": "credential2", "transports": ["internal"]}
        ]

        passkeys = await webauthn_service.list_passkeys("test@example.com")

        assert len(passkeys) == 2
        assert passkeys[0]["id"] == "credential1"


@pytest.mark.asyncio
async def test_delete_passkey():
    """Test deleting a passkey"""
    with patch.object(webauthn_service, 'delete_passkey', new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = True

        result = await webauthn_service.delete_passkey("test@example.com", "credential1")

        assert result is True


@pytest.mark.asyncio
async def test_verify_authentication_invalid_credential():
    """Test authentication with invalid credential"""
    with patch.object(webauthn_service, 'verify_authentication', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = None

        credential = {"id": "invalid_credential"}

        user_email = await webauthn_service.verify_authentication(credential)

        assert user_email is None


@pytest.mark.asyncio
async def test_verify_registration_expired_challenge():
    """Test registration with expired challenge"""
    with patch.object(webauthn_service, 'verify_registration', new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = False

        credential = {"id": "test_credential"}

        result = await webauthn_service.verify_registration("test@example.com", credential)

        assert result is False
