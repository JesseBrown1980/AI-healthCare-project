"""
Field-level encryption utilities for sensitive data.

Provides encryption/decryption for specific database fields based on compliance requirements.
"""

import os
import base64
import logging
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.config.compliance_policies import get_compliance_policy

logger = logging.getLogger(__name__)

# Global encryption key (should be loaded from secure storage in production)
_encryption_key: Optional[bytes] = None
_fernet_instance: Optional[Fernet] = None


def _get_encryption_key() -> bytes:
    """
    Get or generate encryption key for field-level encryption.
    
    In production, this should load from a secure key management service.
    
    Returns:
        Encryption key bytes
    """
    global _encryption_key
    
    if _encryption_key is None:
        # Try to load from environment variable
        key_str = os.getenv("FIELD_ENCRYPTION_KEY")
        
        if key_str:
            try:
                _encryption_key = base64.urlsafe_b64decode(key_str)
            except Exception as e:
                logger.warning(f"Failed to decode encryption key from env: {e}")
                _encryption_key = None
        
        # If not found, generate from master password (development only)
        if _encryption_key is None:
            master_password = os.getenv("MASTER_ENCRYPTION_PASSWORD", "dev-password-change-me")
            salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-me").encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            _encryption_key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            
            if os.getenv("ENVIRONMENT", "development").lower() == "production":
                logger.warning(
                    "Using generated encryption key in production! "
                    "Set FIELD_ENCRYPTION_KEY environment variable."
                )
    
    return _encryption_key


def _get_fernet() -> Fernet:
    """Get Fernet cipher instance for encryption/decryption."""
    global _fernet_instance
    
    if _fernet_instance is None:
        key = _get_encryption_key()
        _fernet_instance = Fernet(key)
    
    return _fernet_instance


def encrypt_field(value: str, field_name: Optional[str] = None) -> Optional[str]:
    """
    Encrypt a field value.
    
    Args:
        value: Plain text value to encrypt
        field_name: Optional field name for logging
        
    Returns:
        Encrypted value as base64 string, or None if encryption not required
    """
    # Check if field-level encryption is required
    policy = get_compliance_policy()
    if not policy.field_level_encryption:
        return value  # Return as-is if not required
    
    if value is None:
        return None
    
    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(value.encode('utf-8'))
        encrypted_str = base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        
        logger.debug(f"Encrypted field: {field_name or 'unknown'}")
        return encrypted_str
    
    except Exception as e:
        logger.error(f"Failed to encrypt field {field_name}: {e}")
        raise


def decrypt_field(value: str, field_name: Optional[str] = None) -> Optional[str]:
    """
    Decrypt a field value.
    
    Args:
        value: Encrypted value as base64 string
        field_name: Optional field name for logging
        
    Returns:
        Decrypted plain text value, or None if value is None
    """
    if value is None:
        return None
    
    # Check if value appears to be encrypted (base64 format)
    try:
        # Try to decode as base64
        decoded = base64.urlsafe_b64decode(value.encode('utf-8'))
        
        # If successful, try to decrypt
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(decoded)
        decrypted_str = decrypted_bytes.decode('utf-8')
        
        logger.debug(f"Decrypted field: {field_name or 'unknown'}")
        return decrypted_str
    
    except Exception:
        # If decryption fails, assume value is not encrypted
        logger.debug(f"Field {field_name or 'unknown'} appears to be unencrypted")
        return value


def encrypt_dict_fields(
    data: Dict[str, Any],
    fields_to_encrypt: list[str],
) -> Dict[str, Any]:
    """
    Encrypt specific fields in a dictionary.
    
    Args:
        data: Dictionary containing fields to encrypt
        fields_to_encrypt: List of field names to encrypt
        
    Returns:
        Dictionary with specified fields encrypted
    """
    encrypted_data = data.copy()
    
    for field_name in fields_to_encrypt:
        if field_name in encrypted_data and encrypted_data[field_name] is not None:
            encrypted_data[field_name] = encrypt_field(
                str(encrypted_data[field_name]),
                field_name=field_name
            )
    
    return encrypted_data


def decrypt_dict_fields(
    data: Dict[str, Any],
    fields_to_decrypt: list[str],
) -> Dict[str, Any]:
    """
    Decrypt specific fields in a dictionary.
    
    Args:
        data: Dictionary containing encrypted fields
        fields_to_decrypt: List of field names to decrypt
        
    Returns:
        Dictionary with specified fields decrypted
    """
    decrypted_data = data.copy()
    
    for field_name in fields_to_decrypt:
        if field_name in decrypted_data and decrypted_data[field_name] is not None:
            decrypted_data[field_name] = decrypt_field(
                str(decrypted_data[field_name]),
                field_name=field_name
            )
    
    return decrypted_data
