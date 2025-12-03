# OAuth Authentication Setup Guide

This guide explains how to set up Google OAuth and Apple Sign-In for user authentication.

## Overview

The system now supports OAuth authentication via:
- **Google OAuth 2.0** - Standard OAuth flow
- **Apple Sign-In** - OAuth 2.0 with Apple-specific requirements

## Features

- ✅ OAuth login (Google & Apple)
- ✅ Automatic user account creation
- ✅ Link OAuth accounts to existing users
- ✅ Token refresh support
- ✅ Secure state management (CSRF protection)

## Setup Instructions

### Google OAuth Setup

1. **Create Google OAuth Credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable "Google+ API" (if needed)
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Web application"
   - Authorized redirect URIs: `http://localhost:8000/auth/oauth/google/callback` (dev)
   - Copy Client ID and Client Secret

2. **Set Environment Variables**
   ```bash
   GOOGLE_OAUTH_CLIENT_ID=your_client_id_here
   GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
   GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/oauth/google/callback
   ```

### Apple Sign-In Setup

1. **Create Apple Developer Account**
   - Sign up at [Apple Developer](https://developer.apple.com/)
   - Enroll in Apple Developer Program ($99/year)

2. **Create App ID and Service ID**
   - Go to [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/identifiers/list)
   - Create an App ID (e.g., `com.yourcompany.healthcare`)
   - Create a Service ID (e.g., `com.yourcompany.healthcare.service`)
   - Configure Service ID:
     - Enable "Sign in with Apple"
     - Add redirect URLs: `http://localhost:8000/auth/oauth/apple/callback`
     - Add domains: `yourdomain.com`

3. **Create Private Key**
   - Go to "Keys" section
   - Create a new key with "Sign in with Apple" enabled
   - Download the `.p8` key file (only available once!)
   - Note the Key ID

4. **Set Environment Variables**
   ```bash
   APPLE_CLIENT_ID=com.yourcompany.healthcare.service
   APPLE_TEAM_ID=your_team_id_here
   APPLE_KEY_ID=your_key_id_here
   APPLE_PRIVATE_KEY=/path/to/AuthKey_XXXXX.p8
   APPLE_REDIRECT_URI=http://localhost:8000/auth/oauth/apple/callback
   ```

## Database Migration

Run the database migration to add OAuth fields:

```bash
# Create migration
alembic revision --autogenerate -m "Add OAuth support to users table"

# Apply migration
alembic upgrade head
```

## API Endpoints

### Initiate OAuth Flow

```
GET /auth/oauth/{provider}/authorize?redirect_after=/dashboard
```

**Providers:** `google`, `apple`

**Query Parameters:**
- `redirect_after` (optional): URL to redirect to after successful login

**Response:** Redirects to provider's authorization page

### OAuth Callback

```
GET /auth/oauth/{provider}/callback?code={code}&state={state}
```

**Response:** Redirects to frontend with JWT token

## Frontend Integration

### Streamlit Frontend

Add OAuth login buttons:

```python
import streamlit as st

col1, col2 = st.columns(2)

with col1:
    google_url = f"{API_URL}/auth/oauth/google/authorize?redirect_after=/"
    st.markdown(f'<a href="{google_url}"><button>Sign in with Google</button></a>', unsafe_allow_html=True)

with col2:
    apple_url = f"{API_URL}/auth/oauth/apple/authorize?redirect_after=/"
    st.markdown(f'<a href="{apple_url}"><button>Sign in with Apple</button></a>', unsafe_allow_html=True)
```

### React Frontend

```typescript
const handleGoogleLogin = () => {
  window.location.href = `${API_URL}/auth/oauth/google/authorize?redirect_after=/dashboard`;
};

const handleAppleLogin = () => {
  window.location.href = `${API_URL}/auth/oauth/apple/authorize?redirect_after=/dashboard`;
};
```

## Security Considerations

### Production Checklist

- [ ] Use HTTPS for all OAuth redirects
- [ ] Store OAuth tokens encrypted in database
- [ ] Use Redis for state management (instead of in-memory)
- [ ] Implement token refresh logic
- [ ] Add rate limiting to OAuth endpoints
- [ ] Verify Apple ID token signatures with Apple's public keys
- [ ] Set secure cookie flags for tokens
- [ ] Implement proper CSRF protection

### Token Encryption

Currently, OAuth tokens are stored in plaintext. In production, encrypt them:

```python
from cryptography.fernet import Fernet

# Generate key once: Fernet.generate_key()
key = os.getenv("OAUTH_ENCRYPTION_KEY")
cipher = Fernet(key)

encrypted_token = cipher.encrypt(token.encode())
decrypted_token = cipher.decrypt(encrypted_token).decode()
```

## Testing

### Test OAuth Flow

1. Start the backend server
2. Navigate to `/auth/oauth/google/authorize`
3. Complete Google sign-in
4. Should redirect back with JWT token

### Test with Postman

1. GET `/auth/oauth/google/authorize?redirect_after=/test`
2. Copy the full redirect URL from response
3. Open in browser and complete OAuth
4. Check callback receives code and state

## Troubleshooting

### Common Issues

**"Invalid redirect URI"**
- Ensure redirect URI in Google/Apple console matches exactly
- Check for trailing slashes
- Verify protocol (http vs https)

**"State token expired"**
- State tokens expire after 10 minutes
- Complete OAuth flow quickly
- In production, use Redis for state storage

**"Email already linked to different provider"**
- User exists with different OAuth provider
- Implement account linking UI
- Or allow multiple OAuth providers per user

## Next Steps

- [ ] Add OAuth account linking UI
- [ ] Implement token refresh on expiry
- [ ] Add OAuth logout (revoke tokens)
- [ ] Support multiple OAuth providers per user
- [ ] Add OAuth provider selection in user settings

