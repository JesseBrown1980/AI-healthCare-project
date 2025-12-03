"""
Authentication module for user management and password handling.
"""

from .password import hash_password, verify_password, is_password_strong

__all__ = ['hash_password', 'verify_password', 'is_password_strong']

