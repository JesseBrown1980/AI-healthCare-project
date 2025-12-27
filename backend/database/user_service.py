"""
User management service for authentication.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from .connection import get_db_session
from .models import User

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""
    
    async def create_user(
        self,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new user account."""
        async with get_db_session() as session:
            # Check if user already exists
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(f"User with email {email} already exists")
            
            user = User(
                id=str(uuid4()),
                email=email.lower(),
                password_hash=password_hash,
                full_name=full_name,
                roles=roles or ['viewer'],
                is_active=1,
                is_verified=0,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            return {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'roles': user.roles,
                'is_active': bool(user.is_active),
            }
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalar_one_or_none()
            if not user:
                return None
            
            return {
                'id': user.id,
                'email': user.email,
                'password_hash': user.password_hash,
                'full_name': user.full_name,
                'roles': user.roles or [],
                'is_active': bool(user.is_active),
                'is_verified': bool(user.is_verified),
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                return None
            
            return {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'roles': user.roles or [],
                'is_active': bool(user.is_active),
                'is_verified': bool(user.is_verified),
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
    
    async def update_user_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.last_login = datetime.now(timezone.utc)
                await session.commit()
    
    async def update_user_password(self, user_id: str, new_password_hash: str) -> None:
        """Update user's password."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.password_hash = new_password_hash
                await session.commit()
    
    async def deactivate_user(self, user_id: str) -> None:
        """Deactivate a user account."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user:
                user.is_active = 0
                await session.commit()
    
    async def generate_password_reset_token(self, email: str) -> Optional[str]:
        """Generate a password reset token for a user."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalar_one_or_none()
            if not user:
                return None  # Don't reveal if user exists
            
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # 1 hour expiry
            
            user.password_reset_token = token
            user.password_reset_token_expires = expires_at
            await session.commit()
            
            return token
    
    async def verify_password_reset_token(self, email: str, token: str) -> bool:
        """Verify a password reset token."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email.lower(),
                    User.password_reset_token == token
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                return False
            
            # Check if token is expired
            if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(timezone.utc):
                return False
            
            return True
    
    async def reset_password_with_token(self, email: str, token: str, new_password_hash: str) -> bool:
        """Reset password using a valid token."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email.lower(),
                    User.password_reset_token == token
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                return False
            
            # Check if token is expired
            if user.password_reset_token_expires and user.password_reset_token_expires < datetime.now(timezone.utc):
                return False
            
            # Update password and clear reset token
            user.password_hash = new_password_hash
            user.password_reset_token = None
            user.password_reset_token_expires = None
            await session.commit()
            
            return True
    
    async def generate_verification_token(self, email: str) -> Optional[str]:
        """Generate an email verification token."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(User.email == email.lower())
            )
            user = result.scalar_one_or_none()
            if not user:
                return None
            
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)  # 7 days expiry
            
            user.verification_token = token
            user.verification_token_expires = expires_at
            await session.commit()
            
            return token
    
    async def verify_email_with_token(self, email: str, token: str) -> bool:
        """Verify email using a verification token."""
        async with get_db_session() as session:
            result = await session.execute(
                select(User).where(
                    User.email == email.lower(),
                    User.verification_token == token
                )
            )
            user = result.scalar_one_or_none()
            if not user:
                return False
            
            # Check if token is expired
            if user.verification_token_expires and user.verification_token_expires < datetime.now(timezone.utc):
                return False
            
            # Mark as verified and clear token
            user.is_verified = 1
            user.verification_token = None
            user.verification_token_expires = None
            await session.commit()
            
            return True

