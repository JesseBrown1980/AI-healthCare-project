import os
import json
import logging
import base64
from typing import Optional, Dict
from pathlib import Path

# Try to import cryptography, else log warning/mock
try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

logger = logging.getLogger(__name__)

class ComplianceService:
    """
    Manages encryption keys for 'Crypto-Shredding' compliance.
    
    Keys are unique per entity (user/patient).
    Deleting a key effectively renders all encrypted data for that entity unreadable,
    satisfying GDPR 'Right to be Forgotten' even in immutable logs.
    """
    
    def __init__(self, key_store_path: str = "compliance_keys.json"):
        self.key_store_path = Path(key_store_path)
        self.keys: Dict[str, str] = {}
        self._load_keys()
        
        if not HAS_CRYPTO:
            logger.warning("ComplianceService: 'cryptography' library not found. Encryption disabled (Plaintext mode).")

    def _load_keys(self):
        if self.key_store_path.exists():
            try:
                self.keys = json.loads(self.key_store_path.read_text(encoding='utf-8'))
            except Exception as e:
                logger.error(f"Failed to load compliance keys: {e}")
                self.keys = {}

    def _save_keys(self):
        try:
            self.key_store_path.write_text(json.dumps(self.keys, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to save compliance keys: {e}")

    def get_or_create_key(self, entity_id: str) -> Optional[bytes]:
        """Retrieve existing key or create a new one for the entity."""
        if not HAS_CRYPTO or not entity_id:
            return None
            
        if entity_id not in self.keys:
            key = Fernet.generate_key().decode('utf-8')
            self.keys[entity_id] = key
            self._save_keys()
            
        return self.keys[entity_id].encode('utf-8')

    def delete_key(self, entity_id: str) -> bool:
        """
        Crypto-shred: Permanently delete the key for an entity.
        This renders all historically encrypted data for this entity unreadable.
        """
        if entity_id in self.keys:
            del self.keys[entity_id]
            self._save_keys()
            logger.info(f"Crypto-shredded key for entity: {entity_id}")
            return True
        return False

    def shred_data(self, data: str, entity_id: str) -> str:
        """Encrypt sensitive data. Returns plaintext if no key/crypto available."""
        if not HAS_CRYPTO or not data or not entity_id:
            return data
            
        key = self.get_or_create_key(entity_id)
        if not key:
            return data
            
        try:
            f = Fernet(key)
            # Prefix to identify encrypted chunks: "ENC:<entity_id>:<ciphertext>"
            # We include entity_id so we know which key to use for decryption
            ciphertext = f.encrypt(data.encode('utf-8')).decode('utf-8')
            return f"ENC:{entity_id}:{ciphertext}"
        except Exception as e:
            logger.error(f"Encryption failed for {entity_id}: {e}")
            return data

    def unshred_data(self, encrypted_data: str) -> str:
        """Decrypt data. Returns original string if not encrypted or key missing."""
        if not HAS_CRYPTO or not encrypted_data or not encrypted_data.startswith("ENC:"):
            return encrypted_data
            
        try:
            # Format: "ENC:<entity_id>:<ciphertext>"
            parts = encrypted_data.split(":", 2)
            if len(parts) != 3:
                return encrypted_data
                
            entity_id = parts[1]
            ciphertext = parts[2]
            
            # If key is gone (deleted via delete_key), we cannot decrypt.
            if entity_id not in self.keys:
                return "[REDACTED/FORGOTTEN]"
                
            key = self.keys[entity_id].encode('utf-8')
            f = Fernet(key)
            return f.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
            
        except Exception as e:
            logger.debug(f"Decryption failed (key likely rotated/deleted): {e}")
            return "[REDACTED/ERROR]"
