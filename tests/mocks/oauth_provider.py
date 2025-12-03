"""
Mock OAuth Provider
Provides mock OAuth tokens and authentication for testing.
"""

from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid
import jwt


# Test secret for signing mock tokens
TEST_JWT_SECRET = "test-secret-key-for-mock-tokens-only"


class MockOAuthProvider:
    """
    Mock OAuth provider for testing authentication flows.
    
    Usage:
        oauth = MockOAuthProvider()
        token = oauth.create_token(user_id="test-user")
    """
    
    def __init__(self, provider: str = "google"):
        self.provider = provider
        self.users: Dict[str, Dict[str, Any]] = {}
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self._valid_codes: Dict[str, str] = {}  # auth_code -> user_id
    
    def add_user(
        self,
        user_id: str,
        email: str,
        name: str = "Test User",
        **kwargs
    ) -> "MockOAuthProvider":
        """Add a test user."""
        self.users[user_id] = {
            "id": user_id,
            "email": email,
            "name": name,
            "email_verified": True,
            "picture": f"https://example.com/avatar/{user_id}.jpg",
            "provider": self.provider,
            **kwargs
        }
        return self
    
    def create_auth_code(self, user_id: str) -> str:
        """Create an authorization code for a user."""
        code = f"auth_code_{uuid.uuid4().hex}"
        self._valid_codes[code] = user_id
        return code
    
    def create_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a mock OAuth token."""
        now = datetime.utcnow()
        exp = now + timedelta(seconds=expires_in)
        
        # Get user info or create default
        user = self.users.get(user_id, {
            "id": user_id,
            "email": email or f"{user_id}@test.example.com",
            "name": "Test User",
        })
        
        # Create JWT access token
        payload = {
            "sub": user_id,
            "email": user.get("email"),
            "name": user.get("name"),
            "iat": now,
            "exp": exp,
            "iss": f"mock-{self.provider}",
            "aud": "test-client-id",
            "scopes": scopes or ["openid", "email", "profile"],
        }
        
        access_token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        
        # Create refresh token
        refresh_payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=30),
        }
        refresh_token = jwt.encode(refresh_payload, TEST_JWT_SECRET, algorithm="HS256")
        
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": " ".join(scopes or ["openid", "email", "profile"]),
            "id_token": access_token,  # Simplified: same as access token
        }
        
        self.tokens[access_token] = {
            "user_id": user_id,
            "expires_at": exp,
            **token_data
        }
        
        return token_data
    
    def exchange_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        user_id = self._valid_codes.pop(code, None)
        if user_id:
            return self.create_token(user_id)
        return None
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a token and return user info."""
        try:
            payload = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
            user_id = payload.get("sub")
            return self.users.get(user_id, {
                "id": user_id,
                "email": payload.get("email"),
                "name": payload.get("name"),
            })
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user info from token (simulates /userinfo endpoint)."""
        return self.validate_token(token)
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False


def create_test_user_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    roles: Optional[List[str]] = None,
) -> str:
    """
    Create a simple test JWT token.
    
    Usage:
        token = create_test_user_token(user_id="user-123")
        headers = {"Authorization": f"Bearer {token}"}
    """
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "roles": roles or ["user"],
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@contextmanager
def mock_oauth_token(user_id: str = "test-user", email: str = "test@example.com"):
    """
    Context manager to mock OAuth token validation.
    
    Usage:
        with mock_oauth_token(user_id="user-123") as token:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/protected", headers=headers)
    """
    provider = MockOAuthProvider()
    provider.add_user(user_id, email)
    token_data = provider.create_token(user_id, email)
    token = token_data["access_token"]
    
    async def mock_validate(*args, **kwargs):
        return provider.validate_token(token)
    
    def mock_validate_sync(*args, **kwargs):
        return provider.validate_token(token)
    
    with patch("backend.auth.security.validate_token", side_effect=mock_validate_sync):
        with patch("backend.auth.security.get_current_user", return_value=provider.users.get(user_id)):
            yield token
