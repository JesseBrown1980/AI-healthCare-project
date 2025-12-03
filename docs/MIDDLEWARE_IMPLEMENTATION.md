# Production Middleware Implementation

## Overview

This document describes the production-ready middleware components added to the Healthcare AI Assistant to enhance security, performance, and reliability.

## Implemented Middleware

### 1. Rate Limiting Middleware (`RateLimitMiddleware`)

**Purpose**: Protect the API from abuse and DoS attacks.

**Features**:
- Sliding window algorithm for accurate rate limiting
- Per-IP and per-user rate limiting (when authenticated)
- Multiple limits:
  - Burst limit: 10 requests per 10 seconds (default)
  - Per-minute limit: 60 requests per minute (default)
  - Per-hour limit: 1000 requests per hour (default)
- Automatic cleanup of old entries to prevent memory leaks
- Rate limit headers in responses (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- `Retry-After` header for rate-limited requests

**Configuration** (via environment variables):
- `RATE_LIMIT_ENABLED`: Enable/disable rate limiting (default: `true`)
- `RATE_LIMIT_PER_MINUTE`: Requests per minute (default: `60`)
- `RATE_LIMIT_PER_HOUR`: Requests per hour (default: `1000`)
- `RATE_LIMIT_BURST`: Burst size (default: `10`)

**Exemptions**:
- Health check endpoints (`/health`, `/api/v1/health`)
- API documentation (`/docs`, `/openapi.json`, `/redoc`)

**Production Note**: For production, consider using Redis-based rate limiting for distributed systems.

### 2. Timeout Middleware (`TimeoutMiddleware`)

**Purpose**: Prevent long-running requests from blocking the server.

**Features**:
- Configurable timeout per endpoint
- Default timeout: 30 seconds
- Extended timeouts for specific endpoints:
  - Patient analysis: 120 seconds
  - Document upload: 60 seconds
  - OCR processing: 180 seconds
  - LLM queries: 60 seconds
- Graceful timeout handling with informative error messages
- `Retry-After` header for timeout responses

**Configuration**:
- `TIMEOUT_MIDDLEWARE_ENABLED`: Enable/disable timeout middleware (default: `true`)
- `REQUEST_TIMEOUT_SECONDS`: Default timeout in seconds (default: `30.0`)

**Exemptions**:
- Health check endpoints

### 3. Security Headers Middleware (`SecurityHeadersMiddleware`)

**Purpose**: Add security headers to all responses for production security.

**Security Headers Added**:
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-XSS-Protection: 1; mode=block` - Enables XSS protection
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer information
- `Permissions-Policy` - Restricts browser features (geolocation, microphone, camera, etc.)
- `Content-Security-Policy` - Custom CSP for API endpoints
- `Strict-Transport-Security` - HSTS header (HTTPS only, when enabled)

**Configuration**:
- `SECURITY_HEADERS_ENABLED`: Enable/disable security headers (default: `true`)
- `HSTS_ENABLED`: Enable HSTS header (default: `true`)

**Production Note**: HSTS header is only added for HTTPS requests.

### 4. Request Size Limits

**Purpose**: Prevent large request payloads from consuming server resources.

**Implementation**:
- FastAPI `max_request_size` parameter
- Default: 10MB
- Configurable via `MAX_REQUEST_SIZE` environment variable

**Note**: For file uploads, consider using streaming uploads for larger files.

## Middleware Execution Order

Middleware in FastAPI executes in reverse order of addition (last added = first executed):

1. **Security Headers** (first added, last executed) - Applies headers to all responses
2. **Timeout** (second) - Enforces request timeouts
3. **Rate Limiting** (third) - Checks rate limits
4. **CORS** (fourth) - Handles CORS headers
5. **Correlation ID** (last) - Adds correlation IDs

## Error Responses

All middleware returns consistent error responses:

```json
{
  "status": "error",
  "message": "Error description",
  "error_type": "rate_limit_exceeded|timeout|...",
  "path": "/api/v1/endpoint",
  ...
}
```

## Testing

To test the middleware:

1. **Rate Limiting**: Make rapid requests to any endpoint
   ```bash
   for i in {1..20}; do curl http://localhost:8000/api/v1/health; done
   ```

2. **Timeout**: Make a request to a slow endpoint
   ```bash
   curl http://localhost:8000/api/v1/analyze-patient
   ```

3. **Security Headers**: Check response headers
   ```bash
   curl -I http://localhost:8000/api/v1/health
   ```

## Production Recommendations

1. **Rate Limiting**: Use Redis-based rate limiting for distributed systems
2. **Monitoring**: Add metrics for rate limit hits and timeouts
3. **Alerting**: Set up alerts for excessive rate limiting or timeouts
4. **Tuning**: Adjust limits based on actual usage patterns
5. **Caching**: Consider caching responses to reduce load

## Environment Variables Summary

```bash
# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
RATE_LIMIT_BURST=10

# Timeout
TIMEOUT_MIDDLEWARE_ENABLED=true
REQUEST_TIMEOUT_SECONDS=30.0

# Security Headers
SECURITY_HEADERS_ENABLED=true
HSTS_ENABLED=true

# Request Size
MAX_REQUEST_SIZE=10485760  # 10MB in bytes
```

## Future Enhancements

- [ ] Redis-based rate limiting for distributed systems
- [ ] Per-endpoint rate limit configuration
- [ ] Request size limits per endpoint
- [ ] Metrics and monitoring integration
- [ ] IP whitelist/blacklist support
- [ ] Rate limit bypass for trusted clients

