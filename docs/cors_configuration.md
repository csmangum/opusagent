# CORS Configuration

This document explains how to configure Cross-Origin Resource Sharing (CORS) for the OpusAgent application.

## Overview

The OpusAgent application uses a centralized configuration system for CORS settings, allowing you to control which origins can access the API endpoints. This is particularly important for security in production environments.

## Configuration

### Environment Variable

The CORS configuration is controlled by the `ALLOWED_ORIGINS` environment variable:

```bash
# Allow all origins (default, not recommended for production)
export ALLOWED_ORIGINS="*"

# Allow specific origins
export ALLOWED_ORIGINS="https://audiocodes.com,https://twilio.com,https://your-domain.com"

# Allow multiple origins with different protocols
export ALLOWED_ORIGINS="https://audiocodes.com,http://localhost:3000,https://your-app.com"
```

### Configuration Structure

The CORS settings are defined in the `SecurityConfig` class:

```python
@dataclass
class SecurityConfig:
    """Security-related configuration."""
    api_key_validation: bool = True
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 100
    require_ssl: bool = False
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
```

## Implementation Details

### CORS Middleware Configuration

The application uses FastAPI's CORS middleware with the following settings:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "WEBSOCKET"],
    allow_headers=["*"],
)
```

### Key Features

1. **Centralized Configuration**: CORS settings are managed through the centralized config system
2. **Environment Variable Support**: Easy configuration via `ALLOWED_ORIGINS` environment variable
3. **Multiple Origins**: Support for multiple allowed origins separated by commas
4. **Wildcard Support**: Support for wildcard (`*`) origin for development
5. **Restricted Methods**: Only allows GET, POST, and WEBSOCKET methods
6. **Credentials Support**: Allows credentials for authenticated requests

## Security Considerations

### Production Recommendations

1. **Avoid Wildcard Origins**: Never use `*` in production
2. **Specific Origins**: Only allow origins that actually need access
3. **HTTPS Only**: Use HTTPS origins in production
4. **Regular Review**: Periodically review and update allowed origins

### Example Production Configuration

```bash
# Production environment
export ALLOWED_ORIGINS="https://your-audiocodes-domain.com,https://your-twilio-domain.com"
export ENV="production"
export REQUIRE_SSL="true"
```

### Development Configuration

```bash
# Development environment
export ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080"
export ENV="development"
export REQUIRE_SSL="false"
```

## API Endpoints

### Configuration Endpoint

You can check the current CORS configuration via the `/config` endpoint:

```bash
curl http://localhost:8000/config
```

Response includes security settings:

```json
{
  "security": {
    "allowed_origins": ["https://audiocodes.com", "https://twilio.com"],
    "api_key_validation": true,
    "rate_limiting_enabled": true,
    "max_requests_per_minute": 100,
    "require_ssl": false
  }
}
```

### Root Endpoint

The root endpoint (`/`) also shows CORS configuration in the environment variables section:

```json
{
  "environment_variables": {
    "ALLOWED_ORIGINS": "CORS allowed origins (current: ['https://audiocodes.com', 'https://twilio.com'])"
  }
}
```

## Testing

### Manual Testing

Test CORS configuration with curl:

```bash
# Test preflight request
curl -X OPTIONS \
  -H "Origin: https://test.com" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  http://localhost:8000/

# Test actual request
curl -H "Origin: https://test.com" \
  http://localhost:8000/
```

### Automated Testing

Run the CORS tests:

```bash
# Run all tests
python -m pytest tests/opusagent/test_main.py::TestCORSConfiguration -v

# Run specific test
python -m pytest tests/opusagent/test_main.py::TestCORSConfiguration::test_cors_headers_present -v
```

## Troubleshooting

### Common Issues

1. **CORS Errors in Browser**: Check that the origin is in the allowed list
2. **WebSocket Connection Issues**: Ensure the origin is allowed for WebSocket connections
3. **Preflight Failures**: Verify that the requested method is in the allowed methods list

### Debugging

1. Check the current configuration:
   ```bash
   curl http://localhost:8000/config
   ```

2. Check environment variables:
   ```bash
   echo $ALLOWED_ORIGINS
   ```

3. Review application logs for CORS-related errors

## Migration from Hardcoded Configuration

The application previously used hardcoded CORS settings:

```python
# Old configuration (insecure)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
```

The new configuration provides:
- Centralized management through environment variables
- Restricted methods (GET, POST, WEBSOCKET only)
- Better security through explicit origin control
- Integration with the centralized config system

## Related Configuration

CORS settings work together with other security configurations:

- `API_KEY_VALIDATION`: Controls API key validation
- `RATE_LIMITING_ENABLED`: Controls rate limiting
- `REQUIRE_SSL`: Controls SSL requirements
- `MAX_REQUESTS_PER_MINUTE`: Controls rate limiting thresholds

See the main configuration documentation for details on all security settings. 