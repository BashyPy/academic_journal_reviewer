import base64
from io import BytesIO

import pyotp
import qrcode


class TOTPService:
    def generate_secret(self) -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    def get_totp_uri(self, email: str, secret: str, issuer: str = "AARIS") -> str:
        """Generate TOTP provisioning URI for QR code."""
        return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    def generate_qr_code(self, uri: str) -> str:
        """Generate QR code image as base64 string."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()

    def verify_code(self, secret: str, code: str) -> bool:
        """Verify TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)


totp_service = TOTPService()
