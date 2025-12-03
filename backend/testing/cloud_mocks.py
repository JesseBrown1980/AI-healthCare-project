"""
Mock Cloud Provider implementations for Enterprise Testing.

These classes simulate cloud environment behaviors to verify compliance policies
(HIPAA/GDPR) without requiring actual cloud connectivity.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CloudProvider(ABC):
    """Abstract base class for cloud provider mocks."""
    
    def __init__(self, region: str):
        self.region = region
        self.logs: List[Dict] = []
        self.storage: Dict[str, bytes] = {}
        
    @abstractmethod
    def encrypt_data(self, data: str, key_id: str) -> bytes:
        """Simulate data encryption."""
        pass
        
    @abstractmethod
    def log_event(self, message: str, severity: str = "INFO") -> None:
        """Simulate cloud logging."""
        pass
        
    @abstractmethod
    def check_compliance(self) -> Dict[str, bool]:
        """Check if current configuration meets compliance standards."""
        pass

class MockAWS(CloudProvider):
    """Mock AWS implementation."""
    
    def encrypt_data(self, data: str, key_id: str) -> bytes:
        # Simulate KMS encryption
        return f"aws-kms:{key_id}:{data}".encode()
    
    def log_event(self, message: str, severity: str = "INFO") -> None:
        # Simulate CloudWatch Logs
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "service": "cloudwatch",
            "message": message,
            "severity": severity,
            "region": self.region
        })
        
    def check_compliance(self) -> Dict[str, bool]:
        """Check HIPAA/GDPR compliance for AWS."""
        return {
            "encryption_enabled": True,  # Simulate enabled by default
            "logging_active": len(self.logs) >= 0,
            "region_compliant": self.region in ["us-east-1", "eu-central-1"]
        }

class MockAzure(CloudProvider):
    """Mock Azure implementation."""
    
    def encrypt_data(self, data: str, key_id: str) -> bytes:
        # Simulate Key Vault encryption
        return f"azure-kv:{key_id}:{data}".encode()
    
    def log_event(self, message: str, severity: str = "INFO") -> None:
        # Simulate Azure Monitor
        self.logs.append({
            "time": datetime.utcnow().isoformat(),
            "source": "azure-monitor",
            "msg": message,
            "level": severity,
            "location": self.region
        })
        
    def check_compliance(self) -> Dict[str, bool]:
        """Check HIPAA/GDPR compliance for Azure."""
        return {
            "encryption_at_rest": True,
            "audit_logs_enabled": True,
            "geo_redundancy": True
        }

class MockGCP(CloudProvider):
    """Mock GCP implementation."""
    
    def encrypt_data(self, data: str, key_id: str) -> bytes:
        # Simulate Cloud KMS encryption
        return f"gcp-kms:{key_id}:{data}".encode()
    
    def log_event(self, message: str, severity: str = "INFO") -> None:
        # Simulate Cloud Logging
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "logName": "projects/mock-project/logs/app-log",
            "textPayload": message,
            "severity": severity,
            "zone": self.region
        })
        
    def check_compliance(self) -> Dict[str, bool]:
        """Check HIPAA/GDPR compliance for GCP."""
        return {
            "default_encryption": True,
            "access_transparency": True,
            "data_residency": True
        }

def get_cloud_provider(provider_name: str, region: str) -> CloudProvider:
    """Factory to get the appropriate cloud mock."""
    providers = {
        "aws": MockAWS,
        "azure": MockAzure,
        "gcp": MockGCP
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported provider: {provider_name}")
        
    return provider_class(region)
