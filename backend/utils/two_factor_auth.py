"""
Two-Factor Authentication (2FA) utilities.

Provides TOTP-based 2FA for enhanced security, required in some regions (e.g., EU/GDPR).
"""

import os
import logging
import base64
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import pyotp
import qrcode
from io import BytesIO

from backend.config.compliance_policies import get_compliance_policy

logger = logging.getLogger(__name__)


def generate_secret_key() -> str:
    """
    Generate a random secret key for TOTP.
    
    Returns:
        Base32-encoded secret key
    """
    return pyotp.random_base32()


def generate_totp_uri(secret: str, user_email: str, issuer: str = "Healthcare AI Assistant") -> str:
    """
    Generate TOTP URI for QR code generation.
    
    Args:
        secret: TOTP secret key
        user_email: User's email address
        issuer: Service name
        
    Returns:
        TOTP URI string
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(
        name=user_email,
        issuer_name=issuer
    )


def generate_qr_code(uri: str) -> bytes:
    """
    Generate QR code image from TOTP URI.
    
    Args:
        uri: TOTP URI string
        
    Returns:
        PNG image bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def verify_totp(secret: str, token: str, window: int = 1) -> bool:
    """
    Verify a TOTP token.
    
    Args:
        secret: TOTP secret key
        token: 6-digit token to verify
        window: Time window for verification (default: 1, allows current and previous period)
        
    Returns:
        True if token is valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    except Exception as e:
        logger.warning(f"TOTP verification error: {e}")
        return False


def is_2fa_required() -> bool:
    """
    Check if 2FA is required based on compliance policy.
    
    Returns:
        True if 2FA is required, False otherwise
    """
    policy = get_compliance_policy()
    return policy.require_2fa


def generate_backup_codes(count: int = 10) -> list[str]:
    """
    Generate backup codes for 2FA recovery.
    
    Args:
        count: Number of backup codes to generate
        
    Returns:
        List of backup codes (8-digit codes)
    """
    codes = []
    for _ in range(count):
        # Generate 8-digit code
        code = secrets.randbelow(100000000)
        codes.append(f"{code:08d}")
    
    return codes


def verify_backup_code(code: str, stored_codes: list[str]) -> tuple[bool, list[str]]:
    """
    Verify a backup code and remove it from the list if valid.
    
    Args:
        code: Backup code to verify
        stored_codes: List of stored backup codes
        
    Returns:
        Tuple of (is_valid, updated_codes_list)
    """
    if code in stored_codes:
        # Remove used code
        updated_codes = [c for c in stored_codes if c != code]
        return True, updated_codes
    
    return False, stored_codes
