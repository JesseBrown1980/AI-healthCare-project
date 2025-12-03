# Developer Guide

## Overview

This guide provides comprehensive documentation for developers working on the Healthcare AI Assistant project. It covers code patterns, utilities, best practices, and examples.

---

## 📚 Table of Contents

1. [Code Quality Utilities](#code-quality-utilities)
2. [Error Handling Patterns](#error-handling-patterns)
3. [Logging Best Practices](#logging-best-practices)
4. [Input Validation](#input-validation)
5. [Performance Optimization](#performance-optimization)
6. [Testing Guidelines](#testing-guidelines)
7. [API Development](#api-development)

---

## Code Quality Utilities

### Service Error Handler

The `ServiceErrorHandler` provides standardized error handling across all endpoints.

**Location**: `backend/utils/service_error_handler.py`

**Usage**:
```python
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.error_responses import get_correlation_id

@router.get("/endpoint")
async def my_endpoint(request: Request):
    correlation_id = get_correlation_id(request)
    
    try:
        # Your code here
        result = await some_operation()
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "my_endpoint", "context": "value"},
            correlation_id,
            request
        )
```

**Error Mapping**:
- `ValueError` → 400 Bad Request
- `KeyError` → 404 Not Found
- `PermissionError` → 403 Forbidden
- `TimeoutError` → 504 Gateway Timeout
- `ConnectionError` → 503 Service Unavailable
- Unknown errors → 500 Internal Server Error

---

### Structured Logging

Structured logging provides consistent, searchable logs with correlation IDs.

**Location**: `backend/utils/logging_utils.py`

**Usage**:
```python
from backend.utils.logging_utils import log_structured, get_correlation_id

@router.post("/endpoint")
async def my_endpoint(request: Request):
    correlation_id = get_correlation_id(request)
    
    log_structured(
        level="info",
        message="Processing request",
        correlation_id=correlation_id,
        request=request,
        custom_field="value"
    )
    
    # ... processing ...
    
    log_structured(
        level="info",
        message="Request completed",
        correlation_id=correlation_id,
        request=request,
        result_count=10
    )
```

**Log Levels**:
- `debug` - Detailed debugging information
- `info` - General informational messages
- `warning` - Warning messages
- `error` - Error messages

**Configuration**:
Set `STRUCTURED_LOGGING=true` in environment to enable JSON format.

---

## Error Handling Patterns

### Standard Error Response Format

All endpoints use a consistent error response format:

```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Invalid input provided",
  "correlation_id": "abc123..."
}
```

### Creating HTTP Exceptions

Use `create_http_exception` for consistent error responses:

```python
from backend.utils.error_responses import create_http_exception

if not data:
    raise create_http_exception(
        message="Data is required",
        status_code=400,
        error_type="ValidationError"
    )
```

---

## Logging Best Practices

### 1. Always Include Correlation IDs

```python
correlation_id = get_correlation_id(request)
log_structured(level="info", message="...", correlation_id=correlation_id, request=request)
```

### 2. Log at Appropriate Levels

- **Info**: Normal operations, successful requests
- **Warning**: Recoverable issues, fallbacks
- **Error**: Failures, exceptions
- **Debug**: Detailed debugging (only in development)

### 3. Include Context

```python
log_structured(
    level="info",
    message="User authenticated",
    correlation_id=correlation_id,
    request=request,
    user_id=user_id,
    method="oauth",
    provider="google"
)
```

### 4. Log Service Errors

```python
from backend.utils.logging_utils import log_service_error

try:
    result = await service_call()
except Exception as e:
    log_service_error(
        e,
        {"operation": "service_call", "param": value},
        correlation_id,
        request
    )
    raise
```

---

## Input Validation

### Available Validators

**Location**: `backend/utils/validation.py`

**Common Validators**:
```python
from backend.utils.validation import (
    validate_patient_id,
    validate_user_id,
    validate_email,
    validate_password_strength,
    validate_query_string,
    sanitize_sql_input,
    sanitize_xss_input,
    validate_url,
)

# Validate patient ID
patient_id = validate_patient_id(user_input)

# Validate email
email = validate_email(user_email)

# Validate password
password = validate_password_strength(user_password, min_length=8)

# Sanitize user input
safe_input = sanitize_sql_input(user_input, max_length=1000)
safe_text = sanitize_xss_input(user_text, max_length=10000)

# Validate query string
query = validate_query_string(search_query, max_length=500)

# Validate URL
url = validate_url(redirect_url, allowed_schemes=["http", "https"])
```

### Validation in Endpoints

```python
@router.post("/endpoint")
async def my_endpoint(request: Request, patient_id: str):
    correlation_id = get_correlation_id(request)
    
    try:
        # Validate input
        validated_id = validate_patient_id(patient_id)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    # ... rest of endpoint
```

---

## Performance Optimization

### Batch Processing

Use `QueryOptimizer` for efficient batch operations:

```python
from backend.utils.performance_optimization import QueryOptimizer

async def fetch_patient(patient_id: str):
    # Fetch logic here
    return patient_data

# Batch fetch multiple patients
results = await QueryOptimizer.batch_fetch(
    fetch_func=fetch_patient,
    ids=patient_ids,
    batch_size=50,
    max_concurrent=10
)
```

### Async Timing

Use decorators to measure function performance:

```python
from backend.utils.performance_optimization import async_timing_decorator

@async_timing_decorator
async def expensive_operation():
    # Your code here
    pass
```

### Connection Pooling

Connection pooling is already configured in `backend/database/connection.py`:
- Pool size: 10
- Max overflow: 20
- Pool recycle: 3600 seconds
- Pool pre-ping: Enabled

---

## Testing Guidelines

### Test Structure

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_endpoint_success(client):
    # Test implementation
    pass
```

### Mocking Dependencies

```python
with patch("backend.api.v1.endpoints.my_endpoint.get_service") as mock_service:
    mock_service.return_value = MockService()
    # Test code
```

### Testing Error Cases

```python
def test_endpoint_validation_error(client):
    response = client.post("/endpoint", json={"invalid": "data"})
    assert response.status_code == 400
    assert response.json()["error_type"] == "ValidationError"
```

---

## API Development

### Endpoint Template

```python
from fastapi import APIRouter, Depends, Request
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured
from backend.utils.service_error_handler import ServiceErrorHandler
from backend.utils.validation import validate_patient_id

router = APIRouter()

@router.get("/endpoint/{patient_id}")
async def my_endpoint(
    request: Request,
    patient_id: str,
    auth: TokenContext = Depends(auth_dependency({"patient/*.read"})),
    audit_service: AuditService = Depends(get_audit_service),
):
    correlation_id = get_correlation_id(request)
    
    # Validate input
    try:
        validated_id = validate_patient_id(patient_id)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Processing request",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_id
        )
        
        # Business logic here
        result = await process_request(validated_id)
        
        log_structured(
            level="info",
            message="Request completed successfully",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_id
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "my_endpoint", "patient_id": validated_id},
            correlation_id,
            request
        )
```

### Required Imports

Every endpoint file should include:
```python
from backend.utils.error_responses import create_http_exception, get_correlation_id
from backend.utils.logging_utils import log_structured, log_service_error
from backend.utils.service_error_handler import ServiceErrorHandler
```

---

## Middleware

### Performance Monitoring

Automatically tracks request timing and slow queries.

**Configuration**:
- `PERFORMANCE_MONITORING_ENABLED=true`
- `SLOW_REQUEST_THRESHOLD_SECONDS=1.0`

**Access Metrics**:
```python
from backend.middleware.performance_monitoring import get_performance_metrics

metrics = get_performance_metrics()
stats = metrics.get_stats()
```

### Input Validation

Automatically validates and sanitizes request inputs.

**Configuration**:
- `INPUT_VALIDATION_ENABLED=true`
- `INPUT_VALIDATION_STRICT=false` (set to true to reject instead of sanitize)
- `MAX_QUERY_LENGTH=500`
- `MAX_PATH_LENGTH=2000`

### Rate Limiting

Per-IP and per-user rate limiting with headers.

**Configuration**:
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_PER_MINUTE=60`
- `RATE_LIMIT_PER_HOUR=1000`
- `RATE_LIMIT_BURST=10`
- `RATE_LIMIT_USER_PER_MINUTE=0` (0 = same as IP limit)
- `RATE_LIMIT_USER_PER_HOUR=0`

---

## Best Practices

### 1. Always Use Correlation IDs

```python
correlation_id = get_correlation_id(request)
```

### 2. Log All Operations

```python
log_structured(level="info", message="...", correlation_id=correlation_id, request=request)
```

### 3. Validate All Inputs

```python
validated_input = validate_patient_id(user_input)
```

### 4. Use Standardized Error Handling

```python
raise ServiceErrorHandler.handle_service_error(e, context, correlation_id, request)
```

### 5. Include Request Context

Always pass `request` parameter to logging and error handling functions.

---

## Examples

### Complete Endpoint Example

```python
@router.post("/patients/{patient_id}/analyze")
async def analyze_patient(
    request: Request,
    patient_id: str,
    include_recommendations: bool = True,
    patient_analyzer: PatientAnalyzer = Depends(get_patient_analyzer),
    audit_service: AuditService = Depends(get_audit_service),
    auth: TokenContext = Depends(auth_dependency({"patient/*.read"})),
):
    correlation_id = get_correlation_id(request)
    
    # Validate input
    try:
        validated_id = validate_patient_id(patient_id)
    except ValueError as e:
        raise create_http_exception(
            message=str(e),
            status_code=400,
            error_type="ValidationError"
        )
    
    try:
        log_structured(
            level="info",
            message="Starting patient analysis",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_id,
            include_recommendations=include_recommendations
        )
        
        # Business logic
        result = await patient_analyzer.analyze(
            patient_id=validated_id,
            include_recommendations=include_recommendations,
            correlation_id=correlation_id
        )
        
        log_structured(
            level="info",
            message="Patient analysis completed",
            correlation_id=correlation_id,
            request=request,
            patient_id=validated_id
        )
        
        # Audit logging
        if audit_service:
            await audit_service.record_event(
                action="E",
                patient_id=validated_id,
                user_context=auth,
                correlation_id=correlation_id,
                outcome="0",
                outcome_desc="Patient analysis completed",
                event_type="analyze",
                request=request
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise ServiceErrorHandler.handle_service_error(
            e,
            {"operation": "analyze_patient", "patient_id": validated_id},
            correlation_id,
            request
        )
```

---

## Configuration

### Environment Variables

**Logging**:
- `STRUCTURED_LOGGING=true` - Enable JSON logging
- `LOG_LEVEL=INFO` - Set log level
- `DEBUG=false` - Enable debug mode

**Performance**:
- `PERFORMANCE_MONITORING_ENABLED=true`
- `SLOW_REQUEST_THRESHOLD_SECONDS=1.0`

**Security**:
- `INPUT_VALIDATION_ENABLED=true`
- `INPUT_VALIDATION_STRICT=false`
- `RATE_LIMIT_ENABLED=true`

---

## Additional Resources

- **Code Quality Improvements**: `docs/CODE_QUALITY_AND_SECURITY_IMPROVEMENTS.md`
- **API Documentation**: See FastAPI auto-generated docs at `/docs`
- **Testing Plan**: `tests/TESTING_PLAN.md`
- **Project Status**: `NEXT_STEPS_SUMMARY.md`

---

**Last Updated**: 2025-01-03
