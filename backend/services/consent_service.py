"""
Consent management service for GDPR and regional compliance.

Handles user consent for privacy policies, terms of service, and data processing.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Consent
from backend.database.connection import get_db_session
from backend.config.compliance_policies import is_consent_required, get_region

logger = logging.getLogger(__name__)


class ConsentService:
    """Service for managing user consent records."""
    
    CONSENT_TYPES = {
        "privacy_policy": "Privacy Policy",
        "terms_of_service": "Terms of Service",
        "data_processing": "Data Processing",
        "marketing": "Marketing Communications",
        "analytics": "Analytics and Tracking",
    }
    
    def __init__(self):
        """Initialize consent service."""
        self.region = get_region()
        self.consent_required = is_consent_required()
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: str,
        version: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record user consent acceptance.
        
        Args:
            user_id: User ID
            consent_type: Type of consent (privacy_policy, terms_of_service, etc.)
            version: Version of the policy/terms
            ip_address: IP address when consent was given
            user_agent: User agent when consent was given
            metadata: Additional metadata
            
        Returns:
            Consent record ID
        """
        async with get_db_session() as session:
            # Check if there's an existing consent record
            existing = await self.get_consent_status(user_id, consent_type, session=session)
            
            if existing and existing.get("accepted"):
                # Update existing consent
                stmt = select(Consent).where(
                    and_(
                        Consent.user_id == user_id,
                        Consent.consent_type == consent_type,
                        Consent.accepted == 1
                    )
                )
                result = await session.execute(stmt)
                consent = result.scalar_one_or_none()
                
                if consent:
                    consent.version = version or consent.version
                    consent.accepted_at = datetime.now(timezone.utc)
                    consent.ip_address = ip_address
                    consent.user_agent = user_agent
                    consent.consent_metadata = metadata or consent.consent_metadata
                    consent.updated_at = datetime.now(timezone.utc)
                    await session.flush()
                    return consent.id
            
            # Create new consent record
            consent = Consent(
                id=str(uuid4()),
                user_id=user_id,
                consent_type=consent_type,
                version=version,
                accepted=1,
                accepted_at=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                consent_metadata=metadata or {},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(consent)
            await session.flush()
            return consent.id
    
    async def withdraw_consent(
        self,
        user_id: str,
        consent_type: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> bool:
        """
        Withdraw user consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent to withdraw
            ip_address: IP address when consent was withdrawn
            user_agent: User agent when consent was withdrawn
            
        Returns:
            True if consent was withdrawn, False if no active consent found
        """
        async with get_db_session() as session:
            stmt = select(Consent).where(
                and_(
                    Consent.user_id == user_id,
                    Consent.consent_type == consent_type,
                    Consent.accepted == 1
                )
            )
            result = await session.execute(stmt)
            consent = result.scalar_one_or_none()
            
            if consent:
                consent.accepted = 0
                consent.withdrawn_at = datetime.now(timezone.utc)
                consent.ip_address = ip_address
                consent.user_agent = user_agent
                consent.updated_at = datetime.now(timezone.utc)
                await session.flush()
                return True
            
            return False
    
    async def get_consent_status(
        self,
        user_id: str,
        consent_type: Optional[str] = None,
        session: Optional[AsyncSession] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get consent status for a user.
        
        Args:
            user_id: User ID
            consent_type: Optional specific consent type to check
            session: Optional database session (for transactions)
            
        Returns:
            Consent status dictionary or None if not found
        """
        if session:
            # Use provided session (assume it's already in a transaction context)
            return await self._get_consent_status_internal(user_id, consent_type, session)
        else:
            # Create new session
            async with get_db_session() as session:
                return await self._get_consent_status_internal(user_id, consent_type, session)
    
    async def _get_consent_status_internal(
        self,
        user_id: str,
        consent_type: Optional[str],
        session: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        """Internal method to get consent status with a session."""
        if consent_type:
            stmt = select(Consent).where(
                and_(
                    Consent.user_id == user_id,
                    Consent.consent_type == consent_type
                )
            ).order_by(Consent.created_at.desc())
        else:
            # Get all consents for user
            stmt = select(Consent).where(
                Consent.user_id == user_id
            ).order_by(Consent.created_at.desc())
        
        result = await session.execute(stmt)
        consents = result.scalars().all()
        
        if not consents:
            return None
        
        if consent_type:
            # Return most recent consent for this type
            consent = consents[0]
            return {
                "user_id": consent.user_id,
                "consent_type": consent.consent_type,
                "version": consent.version,
                "accepted": bool(consent.accepted),
                "accepted_at": consent.accepted_at.isoformat() if consent.accepted_at else None,
                "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
                "metadata": consent.metadata or {},
            }
        else:
            # Return all consents as a dictionary
            return {
                c.consent_type: {
                    "version": c.version,
                    "accepted": bool(c.accepted),
                    "accepted_at": c.accepted_at.isoformat() if c.accepted_at else None,
                    "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
                    "metadata": c.consent_metadata or {},
                }
                for c in consents
            }
    
    async def has_required_consent(self, user_id: str) -> bool:
        """
        Check if user has all required consents based on region policy.
        
        Args:
            user_id: User ID
            
        Returns:
            True if user has all required consents, False otherwise
        """
        if not self.consent_required:
            # Consent not required for this region
            return True
        
        # Check for required consent types (privacy_policy and data_processing for GDPR)
        required_types = ["privacy_policy", "data_processing"]
        
        for consent_type in required_types:
            status = await self.get_consent_status(user_id, consent_type)
            if not status or not status.get("accepted"):
                return False
        
        return True
    
    async def get_all_user_consents(self, user_id: str) -> Dict[str, Any]:
        """
        Get all consent records for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of all consent types and their status
        """
        status = await self.get_consent_status(user_id)
        return status or {}
