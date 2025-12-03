"""
PHI Filter
Detects and redacts Protected Health Information from text.
HIPAA-compliant pattern detection for SSN, MRN, phone, email, DOB, etc.
"""

import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class PHIType(str, Enum):
    """Types of PHI that can be detected."""
    SSN = "ssn"
    MRN = "mrn"
    PHONE = "phone"
    EMAIL = "email"
    DOB = "date_of_birth"
    ADDRESS = "address"
    NAME = "name"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"


@dataclass
class PHIMatch:
    """Represents a detected PHI match."""
    phi_type: PHIType
    start: int
    end: int
    original: str
    redacted: str


class PHIFilter:
    """
    Detects and redacts PHI from text content.
    
    Supports configurable patterns and redaction styles.
    
    Usage:
        filter = PHIFilter()
        clean_text = filter.redact("Patient SSN: 123-45-6789")
        # Returns: "Patient SSN: [SSN REDACTED]"
    """
    
    # Default redaction format
    REDACTION_FORMAT = "[{type} REDACTED]"
    
    # Regex patterns for PHI detection
    PATTERNS = {
        PHIType.SSN: [
            r'\b\d{3}-\d{2}-\d{4}\b',  # 123-45-6789
            r'\b\d{3}\s\d{2}\s\d{4}\b',  # 123 45 6789
            r'\b\d{9}\b(?=\D|$)',  # 123456789 (context-aware)
        ],
        PHIType.MRN: [
            r'\bMRN[:\s#]*\d{6,12}\b',  # MRN: 123456
            r'\b[A-Z]{2,3}\d{6,10}\b',  # AB123456
        ],
        PHIType.PHONE: [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 123-456-7890
            r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',  # (123) 456-7890
            r'\+1\s?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # +1 123-456-7890
        ],
        PHIType.EMAIL: [
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        ],
        PHIType.DOB: [
            r'\b(?:DOB|Date of Birth|Birth Date)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # MM/DD/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY-MM-DD
        ],
        PHIType.CREDIT_CARD: [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 1234-5678-9012-3456
        ],
        PHIType.IP_ADDRESS: [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # 192.168.1.1
        ],
    }
    
    # Compiled patterns cache - NOTE: This is class-level for default patterns only
    # Instance-specific patterns are stored in self._instance_patterns
    
    def __init__(
        self,
        enabled_types: Optional[List[PHIType]] = None,
        redaction_format: Optional[str] = None,
        preserve_length: bool = False,
    ):
        """
        Initialize PHI filter.
        
        Args:
            enabled_types: PHI types to detect (None = all)
            redaction_format: Custom redaction format string
            preserve_length: If True, use asterisks to preserve length
        """
        self.enabled_types = enabled_types or list(PHIType)
        self.redaction_format = redaction_format or self.REDACTION_FORMAT
        self.preserve_length = preserve_length
        
        # Instance-level compiled patterns (not shared with other instances)
        self._instance_patterns: Dict[PHIType, List[re.Pattern]] = {}
        
        # Compile patterns for this specific instance
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for enabled types."""
        # Clear any existing patterns for this instance
        self._instance_patterns.clear()
        
        for phi_type in self.enabled_types:
            if phi_type in self.PATTERNS:
                self._instance_patterns[phi_type] = [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in self.PATTERNS[phi_type]
                ]
    
    def detect(self, text: str) -> List[PHIMatch]:
        """
        Detect PHI in text without redacting.
        
        Args:
            text: Text to scan for PHI
            
        Returns:
            List of PHIMatch objects
        """
        matches = []
        
        for phi_type, patterns in self._instance_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    original = match.group()
                    redacted = self._get_redaction(phi_type, original)
                    
                    matches.append(PHIMatch(
                        phi_type=phi_type,
                        start=match.start(),
                        end=match.end(),
                        original=original,
                        redacted=redacted,
                    ))
        
        # Sort by position and remove overlaps
        matches.sort(key=lambda m: m.start)
        return self._remove_overlaps(matches)
    
    def _remove_overlaps(self, matches: List[PHIMatch]) -> List[PHIMatch]:
        """Remove overlapping matches, keeping longest."""
        if not matches:
            return []
        
        result = [matches[0]]
        for match in matches[1:]:
            if match.start >= result[-1].end:
                result.append(match)
            elif len(match.original) > len(result[-1].original):
                result[-1] = match
        
        return result
    
    def _get_redaction(self, phi_type: PHIType, original: str) -> str:
        """Get redaction string for a match."""
        if self.preserve_length:
            return "*" * len(original)
        return self.redaction_format.format(type=phi_type.value.upper())
    
    def redact(self, text: str) -> str:
        """
        Detect and redact PHI from text.
        
        Args:
            text: Text to redact PHI from
            
        Returns:
            Text with PHI redacted
        """
        matches = self.detect(text)
        
        if not matches:
            return text
        
        # Build result string
        result = []
        last_end = 0
        
        for match in matches:
            result.append(text[last_end:match.start])
            result.append(match.redacted)
            last_end = match.end
        
        result.append(text[last_end:])
        return "".join(result)
    
    def contains_phi(self, text: str) -> bool:
        """Check if text contains any PHI."""
        return len(self.detect(text)) > 0
    
    def get_phi_summary(self, text: str) -> Dict[str, int]:
        """Get count of each PHI type found."""
        matches = self.detect(text)
        summary = {}
        
        for match in matches:
            key = match.phi_type.value
            summary[key] = summary.get(key, 0) + 1
        
        return summary


# Global instance for convenience
_default_filter: Optional[PHIFilter] = None


def get_phi_filter() -> PHIFilter:
    """Get the default PHI filter instance."""
    global _default_filter
    if _default_filter is None:
        _default_filter = PHIFilter()
    return _default_filter


def redact_phi(text: str) -> str:
    """Convenience function to redact PHI from text."""
    return get_phi_filter().redact(text)


def contains_phi(text: str) -> bool:
    """Convenience function to check if text contains PHI."""
    return get_phi_filter().contains_phi(text)
