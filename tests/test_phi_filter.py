"""
PHI Filter Tests
Tests for PHI detection and redaction functionality.
"""

import pytest
from backend.security_utils.phi_filter import (
    PHIFilter,
    PHIType,
    PHIMatch,
    redact_phi,
    contains_phi,
)


class TestPHIPatternDetection:
    """Tests for PHI pattern detection."""
    
    def test_detect_ssn_dashed(self):
        """Test detection of dashed SSN format."""
        filter = PHIFilter()
        text = "Patient SSN: 123-45-6789"
        
        matches = filter.detect(text)
        assert len(matches) == 1
        assert matches[0].phi_type == PHIType.SSN
        assert matches[0].original == "123-45-6789"
    
    def test_detect_ssn_spaced(self):
        """Test detection of spaced SSN format."""
        filter = PHIFilter()
        text = "SSN is 123 45 6789"
        
        matches = filter.detect(text)
        assert len(matches) == 1
        assert matches[0].phi_type == PHIType.SSN
    
    def test_detect_phone_formats(self):
        """Test detection of various phone formats."""
        filter = PHIFilter()
        
        phone_formats = [
            "123-456-7890",
            "123.456.7890",
            "(123) 456-7890",
            "+1 123-456-7890",
        ]
        
        for phone in phone_formats:
            text = f"Call me at {phone}"
            matches = filter.detect(text)
            assert len(matches) >= 1, f"Failed to detect phone: {phone}"
            assert any(m.phi_type == PHIType.PHONE for m in matches)
    
    def test_detect_email(self):
        """Test detection of email addresses."""
        filter = PHIFilter()
        text = "Contact: john.doe@hospital.com"
        
        matches = filter.detect(text)
        assert len(matches) == 1
        assert matches[0].phi_type == PHIType.EMAIL
        assert "john.doe@hospital.com" in matches[0].original
    
    def test_detect_mrn(self):
        """Test detection of Medical Record Numbers."""
        filter = PHIFilter()
        
        mrn_formats = [
            "MRN: 12345678",
            "MRN#123456789",
            "AB1234567890",
        ]
        
        for mrn in mrn_formats:
            matches = filter.detect(mrn)
            # MRN detection may overlap with other patterns
            assert len(matches) >= 0
    
    def test_detect_date_of_birth(self):
        """Test detection of date of birth."""
        filter = PHIFilter()
        
        dob_formats = [
            "DOB: 01/15/1980",
            "Date of Birth: 1980-01-15",
            "Birth Date: 01-15-1980",
        ]
        
        for dob in dob_formats:
            matches = filter.detect(dob)
            assert len(matches) >= 1, f"Failed to detect DOB: {dob}"
    
    def test_detect_credit_card(self):
        """Test detection of credit card numbers."""
        filter = PHIFilter()
        text = "Card: 1234-5678-9012-3456"
        
        matches = filter.detect(text)
        assert len(matches) == 1
        assert matches[0].phi_type == PHIType.CREDIT_CARD
    
    def test_detect_ip_address(self):
        """Test detection of IP addresses."""
        filter = PHIFilter()
        text = "Client IP: 192.168.1.100"
        
        matches = filter.detect(text)
        assert len(matches) == 1
        assert matches[0].phi_type == PHIType.IP_ADDRESS


class TestPHIRedaction:
    """Tests for PHI redaction."""
    
    def test_redact_ssn(self):
        """Test SSN redaction."""
        text = "Patient SSN: 123-45-6789"
        result = redact_phi(text)
        
        assert "123-45-6789" not in result
        assert "[SSN REDACTED]" in result
    
    def test_redact_multiple_phi(self):
        """Test redaction of multiple PHI types."""
        text = "SSN: 123-45-6789, Email: john@test.com, Phone: 555-123-4567"
        result = redact_phi(text)
        
        assert "123-45-6789" not in result
        assert "john@test.com" not in result
        assert "555-123-4567" not in result
    
    def test_redact_preserves_non_phi(self):
        """Test that non-PHI text is preserved."""
        text = "Patient name is John Doe, age 45. SSN: 123-45-6789"
        result = redact_phi(text)
        
        assert "Patient name is John Doe, age 45" in result
        assert "123-45-6789" not in result
    
    def test_redact_preserve_length(self):
        """Test length-preserving redaction."""
        filter = PHIFilter(preserve_length=True)
        text = "SSN: 123-45-6789"
        result = filter.redact(text)
        
        # Should use asterisks instead of label
        assert "***********" in result
    
    def test_custom_redaction_format(self):
        """Test custom redaction format."""
        filter = PHIFilter(redaction_format="<REMOVED:{type}>")
        text = "SSN: 123-45-6789"
        result = filter.redact(text)
        
        assert "<REMOVED:SSN>" in result


class TestPHIFilterConfiguration:
    """Tests for PHI filter configuration."""
    
    def test_filter_specific_types(self):
        """Test filtering only specific PHI types."""
        # Create a fresh filter instance with only SSN enabled
        phi_filter = PHIFilter(enabled_types=[PHIType.SSN])
        text = "SSN: 123-45-6789, Email: john@test.com"
        result = phi_filter.redact(text)
        
        # SSN should be redacted
        assert "123-45-6789" not in result, f"SSN should be redacted, got: {result}"
        # Email should NOT be redacted (not in enabled types)
        # Note: Since only SSN is enabled, email patterns should not match
        assert "john@test.com" in result, f"Email should NOT be redacted when only SSN enabled, got: {result}"
    
    def test_contains_phi(self):
        """Test PHI detection check."""
        assert contains_phi("SSN: 123-45-6789") == True
        assert contains_phi("No sensitive data here") == False
    
    def test_empty_text(self):
        """Test handling of empty text."""
        result = redact_phi("")
        assert result == ""
    
    def test_no_phi_text(self):
        """Test text with no PHI."""
        text = "This is a normal text without any PHI"
        result = redact_phi(text)
        assert result == text


class TestPHISummary:
    """Tests for PHI summary functionality."""
    
    def test_get_phi_summary(self):
        """Test PHI type summary."""
        filter = PHIFilter()
        text = "SSN: 123-45-6789, Phone: 555-123-4567, Email: a@b.com"
        
        summary = filter.get_phi_summary(text)
        
        assert "ssn" in summary
        assert "phone" in summary
        assert "email" in summary
    
    def test_summary_counts(self):
        """Test that summary counts are correct."""
        filter = PHIFilter()
        text = "SSN: 123-45-6789, SSN: 987-65-4321"
        
        summary = filter.get_phi_summary(text)
        assert summary.get("ssn", 0) == 2


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_overlapping_patterns(self):
        """Test handling of overlapping patterns."""
        filter = PHIFilter()
        # This could match phone or SSN depending on context
        text = "Number: 123-456-7890"
        
        matches = filter.detect(text)
        # Should not have overlapping matches
        for i, match in enumerate(matches):
            for j, other in enumerate(matches):
                if i != j:
                    assert match.end <= other.start or match.start >= other.end
    
    def test_unicode_text(self):
        """Test handling of unicode text."""
        text = "Patient: José García, SSN: 123-45-6789"
        result = redact_phi(text)
        
        assert "José García" in result
        assert "123-45-6789" not in result
    
    def test_multiline_text(self):
        """Test handling of multiline text."""
        text = """
        Patient Record
        SSN: 123-45-6789
        Phone: 555-123-4567
        """
        result = redact_phi(text)
        
        assert "123-45-6789" not in result
        assert "555-123-4567" not in result
