"""
Input validation utilities for security and data integrity.

Provides common validation functions for IDs, filenames, and other inputs.
"""

import re
import os
from typing import Optional
from fastapi import HTTPException


# Common validation patterns
PATIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,255}$')
USER_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,255}$')
DOCUMENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,255}$')
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
OAUTH_PROVIDER_PATTERN = re.compile(r'^(google|apple|microsoft)$', re.IGNORECASE)
FILENAME_PATTERN = re.compile(r'^[a-zA-Z0-9._-]{1,255}$')

# Dangerous filename patterns (path traversal, etc.)
DANGEROUS_FILENAME_PATTERNS = [
    r'\.\.',  # Path traversal
    r'/',     # Directory separator
    r'\\',    # Windows directory separator
    r'\x00',  # Null byte
]


def validate_patient_id(patient_id: str) -> str:
    """
    Validate and sanitize patient ID.
    
    Args:
        patient_id: Patient ID to validate
        
    Returns:
        Sanitized patient ID
        
    Raises:
        HTTPException: If patient ID is invalid
    """
    if not patient_id:
        raise HTTPException(status_code=400, detail="Patient ID is required")
    
    patient_id = patient_id.strip()
    
    if not PATIENT_ID_PATTERN.match(patient_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid patient ID format. Must contain only alphanumeric characters, hyphens, and underscores (max 255 characters)"
        )
    
    return patient_id


def validate_user_id(user_id: str) -> str:
    """
    Validate and sanitize user ID.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        Sanitized user ID
        
    Raises:
        HTTPException: If user ID is invalid
    """
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    user_id = user_id.strip()
    
    if not USER_ID_PATTERN.match(user_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid user ID format. Must contain only alphanumeric characters, hyphens, and underscores (max 255 characters)"
        )
    
    return user_id


def validate_document_id(document_id: str) -> str:
    """
    Validate and sanitize document ID.
    
    Args:
        document_id: Document ID to validate
        
    Returns:
        Sanitized document ID
        
    Raises:
        HTTPException: If document ID is invalid
    """
    if not document_id:
        raise HTTPException(status_code=400, detail="Document ID is required")
    
    document_id = document_id.strip()
    
    if not DOCUMENT_ID_PATTERN.match(document_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid document ID format. Must contain only alphanumeric characters, hyphens, and underscores (max 255 characters)"
        )
    
    return document_id


def validate_email(email: str) -> str:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Normalized email address (lowercase)
        
    Raises:
        HTTPException: If email is invalid
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    email = email.strip().lower()
    
    if not EMAIL_PATTERN.match(email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format"
        )
    
    if len(email) > 255:
        raise HTTPException(status_code=400, detail="Email address too long (max 255 characters)")
    
    return email


def validate_oauth_provider(provider: str) -> str:
    """
    Validate OAuth provider name.
    
    Args:
        provider: OAuth provider name to validate
        
    Returns:
        Normalized provider name (lowercase)
        
    Raises:
        HTTPException: If provider is invalid
    """
    if not provider:
        raise HTTPException(status_code=400, detail="OAuth provider is required")
    
    provider = provider.strip().lower()
    
    if not OAUTH_PROVIDER_PATTERN.match(provider):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider: {provider}. Supported providers: google, apple"
        )
    
    return provider


# File size limits (in bytes)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB default
MAX_FILENAME_LENGTH = 255


def validate_file_size(file_size: int, max_size: int = MAX_FILE_SIZE) -> None:
    """
    Validate file size.
    
    Args:
        file_size: File size in bytes
        max_size: Maximum allowed file size in bytes
        
    Raises:
        HTTPException: If file size exceeds limit
    """
    if file_size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {max_size_mb:.1f} MB"
        )


def validate_filename(filename: str) -> str:
    """
    Validate and sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Filename to validate
        
    Returns:
        Sanitized filename (basename only)
        
    Raises:
        HTTPException: If filename is invalid or dangerous
    """
    if not filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Get basename to prevent path traversal
    filename = os.path.basename(filename.strip())
    
    # Check for dangerous patterns
    for pattern in DANGEROUS_FILENAME_PATTERNS:
        if re.search(pattern, filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid filename: contains dangerous characters"
            )
    
    # Validate format
    if not FILENAME_PATTERN.match(filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename format. Must contain only alphanumeric characters, dots, hyphens, and underscores (max 255 characters)"
        )
    
    return filename


def validate_patient_id_list(patient_ids: list[str], max_count: int = 10) -> list[str]:
    """
    Validate a list of patient IDs.
    
    Args:
        patient_ids: List of patient IDs to validate
        max_count: Maximum number of patient IDs allowed
    
    Returns:
        List of validated patient IDs
    
    Raises:
        HTTPException: If validation fails
    """
    if not patient_ids:
        raise HTTPException(status_code=400, detail="Patient IDs list is required")
    
    if len(patient_ids) > max_count:
        raise HTTPException(
            status_code=400,
            detail=f"Too many patient IDs. Maximum {max_count} allowed"
        )
    
    # Validate each patient ID
    validated_ids = []
    seen_ids = set()
    
    for patient_id in patient_ids:
        validated_id = validate_patient_id(patient_id)
        
        # Check for duplicates
        if validated_id in seen_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate patient ID: {validated_id}"
            )
        
        seen_ids.add(validated_id)
        validated_ids.append(validated_id)
    
    return validated_ids


def sanitize_sql_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize input to prevent SQL injection attacks.
    
    Note: This is a basic sanitization. Always use parameterized queries
    in database operations. This function provides an additional layer.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    
    Raises:
        HTTPException: If input contains dangerous patterns
    """
    if not value:
        return value
    
    # Check length
    if len(value) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input too long. Maximum {max_length} characters allowed"
        )
    
    # Dangerous SQL patterns
    dangerous_patterns = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|SCRIPT)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # SQL injection: OR 1=1
        r'(\'|\"|;|--|\*|/\*|\*/)',  # SQL comment and quote patterns
    ]
    
    value_upper = value.upper()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_upper, re.IGNORECASE):
            raise HTTPException(
                status_code=400,
                detail="Input contains potentially dangerous SQL patterns"
            )
    
    return value.strip()


def sanitize_xss_input(value: str, max_length: int = 10000) -> str:
    """
    Sanitize input to prevent XSS (Cross-Site Scripting) attacks.
    
    Note: This is basic sanitization. For production, use a proper HTML sanitizer
    like bleach or html-sanitizer.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length
    
    Returns:
        Sanitized string
    
    Raises:
        HTTPException: If input contains dangerous patterns
    """
    if not value:
        return value
    
    # Check length
    if len(value) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Input too long. Maximum {max_length} characters allowed"
        )
    
    # Dangerous XSS patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
        r'<iframe[^>]*>',  # Iframe tags
        r'<object[^>]*>',  # Object tags
        r'<embed[^>]*>',  # Embed tags
        r'expression\s*\(',  # CSS expressions
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
            raise HTTPException(
                status_code=400,
                detail="Input contains potentially dangerous XSS patterns"
            )
    
    return value.strip()


def validate_query_string(query: str, max_length: int = 500) -> str:
    """
    Validate and sanitize search query strings.
    
    Args:
        query: Query string to validate
        max_length: Maximum allowed length
    
    Returns:
        Sanitized query string
    
    Raises:
        HTTPException: If query is invalid
    """
    if not query:
        raise HTTPException(status_code=400, detail="Query string is required")
    
    query = query.strip()
    
    if len(query) > max_length:
        raise HTTPException(
            status_code=400,
            detail=f"Query string too long. Maximum {max_length} characters allowed"
        )
    
    # Basic sanitization
    query = sanitize_xss_input(query, max_length)
    
    return query


def validate_url(url: str, allowed_schemes: list[str] = None) -> str:
    """
    Validate URL format and scheme.
    
    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: ['http', 'https'])
    
    Returns:
        Validated URL
    
    Raises:
        HTTPException: If URL is invalid
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    url = url.strip()
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Basic URL validation
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        if not parsed.scheme:
            raise HTTPException(status_code=400, detail="URL must include a scheme (http:// or https://)")
        
        if parsed.scheme.lower() not in [s.lower() for s in allowed_schemes]:
            raise HTTPException(
                status_code=400,
                detail=f"URL scheme must be one of: {', '.join(allowed_schemes)}"
            )
        
        if not parsed.netloc:
            raise HTTPException(status_code=400, detail="URL must include a hostname")
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid URL format: {str(e)}")
    
    return url


def validate_password_strength(password: str, min_length: int = 8) -> str:
    """
    Validate password strength.
    
    Args:
        password: Password to validate
        min_length: Minimum password length
    
    Returns:
        Validated password
    
    Raises:
        HTTPException: If password doesn't meet strength requirements
    """
    if not password:
        raise HTTPException(status_code=400, detail="Password is required")
    
    if len(password) < min_length:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {min_length} characters long"
        )
    
    # Check for at least one uppercase letter
    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter"
        )
    
    # Check for at least one lowercase letter
    if not re.search(r'[a-z]', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter"
        )
    
    # Check for at least one digit
    if not re.search(r'\d', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one digit"
        )
    
    # Check for at least one special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character"
        )
    
    return password
