# API Key Usage Guide

## Quick Start

### 1. Generate an API Key

```bash
curl -X POST "http://localhost:8000/api/v1/api-keys" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "My Application Key",
    "scopes": ["read", "write"],
    "rate_limit": 1000,
    "expires_in_days": 90
  }'
```

### 2. Use the API Key

```bash
curl -X GET "http://localhost:8000/api/v1/protected-endpoint" \
  -H "X-API-Key: sk_your_secret_key_here"
```

### 3. Monitor Usage

```bash
curl -X GET "http://localhost:8000/api/v1/api-keys/ak_key_id/analytics" \
  -H "X-API-Key: sk_your_secret_key_here"
```

## Key Features

- **Secure Generation**: HMAC-SHA256 hashing with public/private key pairs
- **Scoped Permissions**: Fine-grained access control per resource
- **Rate Limiting**: Multiple algorithms to prevent abuse
- **Usage Analytics**: Real-time monitoring and insights
- **Lifecycle Management**: Automatic expiration and rotation

## Security Best Practices

1. **Store keys securely** - Never commit keys to version control
2. **Use minimal scopes** - Grant only necessary permissions
3. **Set expiration dates** - Regularly rotate keys
4. **Monitor usage** - Watch for anomalous activity
5. **Use HTTPS** - Encrypt all API communications

For complete API documentation, see the OpenAPI specs at `/docs` when running the server.