"""
OAuth authentication providers (Google, Apple)
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import httpx
from jose import jwt as jose_jwt
import json

logger = logging.getLogger(__name__)


class GoogleOAuthProvider:
    """Google OAuth 2.0 authentication provider."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "")
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF protection state token
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            code: Authorization code from callback
            
        Returns:
            Dictionary with access_token, refresh_token, expires_in, etc.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.token_url,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Google.
        
        Args:
            access_token: OAuth access token
            
        Returns:
            User information dictionary
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: OAuth refresh token
            
        Returns:
            New token information
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            return response.json()


class AppleOAuthProvider:
    """Apple Sign-In (OAuth 2.0) authentication provider."""
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        team_id: Optional[str] = None,
        key_id: Optional[str] = None,
        private_key: Optional[str] = None,
        redirect_uri: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("APPLE_CLIENT_ID", "")
        self.team_id = team_id or os.getenv("APPLE_TEAM_ID", "")
        self.key_id = key_id or os.getenv("APPLE_KEY_ID", "")
        self.private_key = private_key or os.getenv("APPLE_PRIVATE_KEY", "")
        self.redirect_uri = redirect_uri or os.getenv("APPLE_REDIRECT_URI", "")
        self.auth_url = "https://appleid.apple.com/auth/authorize"
        self.token_url = "https://appleid.apple.com/auth/token"
    
    def _generate_client_secret(self) -> str:
        """
        Generate Apple client secret JWT.
        
        Apple requires a JWT signed with your private key as the client secret.
        """
        headers = {
            "kid": self.key_id,
            "alg": "ES256",
        }
        
        payload = {
            "iss": self.team_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc).timestamp() + 3600)),  # 1 hour
            "aud": "https://appleid.apple.com",
            "sub": self.client_id,
        }
        
        # Note: This requires cryptography library and proper key loading
        # For now, return placeholder - actual implementation needs proper key handling
        try:
            import jwt as pyjwt
            # Load private key (Apple provides .p8 file)
            # In production, load from secure storage
            if isinstance(self.private_key, str):
                # If it's a file path, load it
                if self.private_key.endswith('.p8'):
                    with open(self.private_key, 'r') as f:
                        private_key_data = f.read()
                else:
                    private_key_data = self.private_key
            else:
                private_key_data = self.private_key
            
            secret = pyjwt.encode(payload, private_key_data, algorithm="ES256", headers=headers)
            return secret
        except Exception as e:
            logger.error(f"Failed to generate Apple client secret: {e}")
            raise
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate Apple Sign-In authorization URL.
        
        Args:
            state: CSRF protection state token
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "name email",
            "state": state,
            "response_mode": "form_post",  # Apple prefers form_post
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.auth_url}?{query_string}"
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and ID tokens.
        
        Args:
            code: Authorization code from callback
            
        Returns:
            Dictionary with access_token, id_token, refresh_token, etc.
        """
        client_secret = self._generate_client_secret()
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info_from_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Extract user information from Apple ID token.
        
        Apple provides user info in the ID token JWT, not a separate userinfo endpoint.
        
        Args:
            id_token: Apple ID token JWT
            
        Returns:
            User information dictionary
        """
        try:
            # Decode JWT without verification (Apple uses public keys for verification)
            # In production, verify with Apple's public keys
            decoded = jose_jwt.decode(id_token, options={"verify_signature": False})
            
            # Apple provides email in the token
            user_info = {
                "sub": decoded.get("sub"),  # Apple user ID
                "email": decoded.get("email"),
                "email_verified": decoded.get("email_verified", False),
            }
            
            # Name might be in the token if provided during first sign-in
            if "name" in decoded:
                user_info["name"] = decoded["name"]
            
            return user_info
        except Exception as e:
            logger.error(f"Failed to decode Apple ID token: {e}")
            raise


def get_oauth_provider(provider: str) -> Optional[Any]:
    """
    Get OAuth provider instance by name.
    
    Args:
        provider: Provider name ('google' or 'apple')
        
    Returns:
        OAuth provider instance or None
    """
    if provider.lower() == "google":
        return GoogleOAuthProvider()
    elif provider.lower() == "apple":
        return AppleOAuthProvider()
    else:
        return None

