"""
User management service for authentication.
"""

import logging
from datetime import datetime, timezone
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

