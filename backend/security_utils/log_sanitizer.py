"""
Log Sanitizer
Safe logging wrapper that automatically redacts PHI.
"""

import logging
import os
from typing import Any, Dict, Optional
from functools import wraps

from .phi_filter import PHIFilter, redact_phi, PHIType


class SanitizedLogRecord(logging.LogRecord):
    """LogRecord that sanitizes PHI from message."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sanitize the message
        if hasattr(self, 'msg') and isinstance(self.msg, str):
            self.msg = redact_phi(self.msg)


class SanitizingFormatter(logging.Formatter):
    """Formatter that redacts PHI from log messages."""
    
    def __init__(self, *args, phi_filter: Optional[PHIFilter] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.phi_filter = phi_filter or PHIFilter()
    
    def format(self, record: logging.LogRecord) -> str:
        # Sanitize message
        if isinstance(record.msg, str):
            record.msg = self.phi_filter.redact(record.msg)
        
        # Sanitize args if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self.phi_filter.redact(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self.phi_filter.redact(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        return super().format(record)


class SecureLogger:
    """
    Secure logger wrapper that automatically redacts PHI.
    
    Usage:
        logger = SecureLogger(__name__)
        logger.info("Patient SSN: 123-45-6789")
        # Logs: "Patient SSN: [SSN REDACTED]"
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        phi_filter: Optional[PHIFilter] = None,
    ):
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self.phi_filter = phi_filter or PHIFilter()
        
        # Add sanitizing handler if not already present
        self._ensure_sanitizing_handler()
    
    def _ensure_sanitizing_handler(self) -> None:
        """Ensure logger has a sanitizing handler."""
        for handler in self._logger.handlers:
            if isinstance(handler.formatter, SanitizingFormatter):
                return
        
        # Add new handler with sanitizing formatter
        handler = logging.StreamHandler()
        handler.setFormatter(SanitizingFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            phi_filter=self.phi_filter,
        ))
        self._logger.addHandler(handler)
    
    def _sanitize(self, msg: Any) -> str:
        """Sanitize a message."""
        if isinstance(msg, str):
            return self.phi_filter.redact(msg)
        return str(msg)
    
    def _sanitize_args(self, args: tuple) -> tuple:
        """Sanitize log arguments."""
        return tuple(
            self.phi_filter.redact(str(arg)) if isinstance(arg, str) else arg
            for arg in args
        )
    
    def debug(self, msg: Any, *args, **kwargs) -> None:
        self._logger.debug(self._sanitize(msg), *self._sanitize_args(args), **kwargs)
    
    def info(self, msg: Any, *args, **kwargs) -> None:
        self._logger.info(self._sanitize(msg), *self._sanitize_args(args), **kwargs)
    
    def warning(self, msg: Any, *args, **kwargs) -> None:
        self._logger.warning(self._sanitize(msg), *self._sanitize_args(args), **kwargs)
    
    def error(self, msg: Any, *args, **kwargs) -> None:
        self._logger.error(self._sanitize(msg), *self._sanitize_args(args), **kwargs)
    
    def critical(self, msg: Any, *args, **kwargs) -> None:
        self._logger.critical(self._sanitize(msg), *self._sanitize_args(args), **kwargs)
    
    def exception(self, msg: Any, *args, **kwargs) -> None:
        self._logger.exception(self._sanitize(msg), *self._sanitize_args(args), **kwargs)


def get_secure_logger(name: str) -> SecureLogger:
    """Get a secure logger for the given name."""
    return SecureLogger(name)


def sanitize_dict(data: Dict[str, Any], phi_filter: Optional[PHIFilter] = None) -> Dict[str, Any]:
    """
    Recursively sanitize PHI from a dictionary.
    
    Args:
        data: Dictionary to sanitize
        phi_filter: PHI filter to use (default: global filter)
    
    Returns:
        Dictionary with PHI redacted from string values
    """
    if phi_filter is None:
        phi_filter = PHIFilter()
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = phi_filter.redact(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, phi_filter)
        elif isinstance(value, list):
            result[key] = [
                phi_filter.redact(item) if isinstance(item, str)
                else sanitize_dict(item, phi_filter) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def log_sanitized(func):
    """
    Decorator to sanitize PHI from function return values before logging.
    
    Usage:
        @log_sanitized
        def get_patient_data():
            return {"name": "John Doe", "ssn": "123-45-6789"}
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            return sanitize_dict(result)
        elif isinstance(result, str):
            return redact_phi(result)
        return result
    return wrapper


# Configure root logger with sanitizing formatter if in production
def configure_secure_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger with PHI sanitization.
    
    Call this at application startup for automatic PHI redaction.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Replace existing handlers with sanitizing ones
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    handler = logging.StreamHandler()
    handler.setFormatter(SanitizingFormatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ))
    root_logger.addHandler(handler)
