# API Authentication for Mock Payment Ecosystem

## Overview

The Mock Payment Ecosystem integrates seamlessly with the existing API Developer Portal authentication system. All payment APIs require valid API key authentication and follow the same security patterns established in the main platform.

## Authentication Methods

### Primary: API Key Authentication

All payment APIs use the existing X-API-Key header authentication:

```http
GET /marketplace/v1/payments/history
Host: api.portal.dev
X-API-Key: ak_dev_1234567890abcdef1234567890abcdef
Content-Type: application/json
```

### API Key Requirements

#### Scopes for Payment APIs
Payment APIs require specific scopes in addition to basic API access:

- **`payment:read`** - View payment data, transaction history, account information
- **`payment:write`** - Process payments, create refunds, manage payment methods
- **`payment:admin`** - Administrative access, reporting, configuration management
- **`payment:compliance`** - Access compliance reports, audit data, regulatory information

#### Creating Payment-Enabled API Keys

1. **Via Developer Portal Dashboard**:
   ```
   1. Navigate to API Key Management
   2. Click "Create New Key"
   3. Select "Payment Ecosystem Template"
   4. Choose required scopes:
      - payment:read (required)
      - payment:write (for processing)
      - payment:admin (for management)
      - payment:compliance (for reporting)
   5. Set rate limits appropriate for payment volume
   6. Configure IP restrictions if needed
   ```

2. **Via API Management Console**:
   ```bash
   # Create payment-enabled API key
   curl -X POST \
     https://api.portal.dev/api/api-keys \
     -H 'Authorization: Bearer your-jwt-token' \
     -H 'Content-Type: application/json' \
     -d '{
       "name": "Payment Processing Key",
       "scopes": ["payment:read", "payment:write"],
       "rate_limit": 1000,
       "rate_limit_period": "hour",
       "expires_at": "2025-12-31T23:59:59Z"
     }'
   ```

## Security Features

### Rate Limiting
Payment APIs inherit the enhanced rate limiting system:

- **Global Limits**: System-wide protection against abuse
- **Per-Key Limits**: Individual API key quotas
- **Endpoint-Specific**: Different limits for read vs. write operations
- **Burst Protection**: Token bucket algorithm for traffic spikes

```http
# Rate limit headers in responses
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1704067200
X-RateLimit-Algorithm: token-bucket
```

### Enhanced Security Headers

#### Request Headers
```http
X-API-Key: ak_prod_1234567890abcdef1234567890abcdef
X-Request-ID: req_unique_identifier_12345
X-Idempotency-Key: idem_payment_67890 (for write operations)
X-Client-Version: myapp/1.2.3
Content-Type: application/json
```

#### Optional Security Headers
```http
X-Signature: sha256=computed_hmac_signature (for request signing)
X-Timestamp: 1704067200 (for request validation)
X-Client-IP: 192.168.1.100 (for additional security)
```

### Request Signing (Optional)

For high-security environments, implement HMAC-SHA256 request signing:

```javascript
// JavaScript example
const crypto = require('crypto');

function signRequest(method, path, body, timestamp, apiSecret) {
  const payload = `${method}\n${path}\n${body}\n${timestamp}`;
  return crypto
    .createHmac('sha256', apiSecret)
    .update(payload)
    .digest('hex');
}

// Usage
const signature = signRequest('POST', '/marketplace/v1/payments/process', JSON.stringify(requestBody), timestamp, apiSecret);

// Include in request
headers['X-Signature'] = `sha256=${signature}`;
headers['X-Timestamp'] = timestamp;
```

## Environment Configuration

### Sandbox vs. Production-Simulation

#### Sandbox Environment
```
Base URL: https://sandbox-api.portal.dev/marketplace/v1/
Purpose: Development and testing
API Keys: Use keys with 'dev' or 'test' prefix
Rate Limits: Relaxed for testing
Data: Mock data that resets daily
```

#### Production-Simulation Environment
```
Base URL: https://api.portal.dev/marketplace/v1/
Purpose: Pre-production testing with realistic constraints
API Keys: Use production API keys
Rate Limits: Production-level limits enforced
Data: Persistent mock data with realistic scenarios
```

## Error Handling

### Authentication Errors

```json
{
  "error": {
    "code": "authentication_failed",
    "message": "Invalid API key",
    "type": "authentication_error",
    "param": "X-API-Key"
  },
  "request_id": "req_12345"
}
```

### Authorization Errors

```json
{
  "error": {
    "code": "insufficient_permissions",
    "message": "API key lacks required scope: payment:write",
    "type": "authorization_error",
    "required_scope": "payment:write",
    "current_scopes": ["payment:read"]
  },
  "request_id": "req_12346"
}
```

### Rate Limit Errors

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Request rate limit exceeded",
    "type": "rate_limit_error",
    "retry_after": 300
  },
  "request_id": "req_12347"
}
```

## Integration Examples

### Python Integration

```python
import requests
import hmac
import hashlib
import time
import json

class PaymentAPIClient:
    def __init__(self, api_key, base_url="https://api.portal.dev/marketplace/v1", api_secret=None):
        self.api_key = api_key
        self.base_url = base_url
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'PaymentClient/1.0'
        })
    
    def _sign_request(self, method, path, body):
        if not self.api_secret:
            return None
        
        timestamp = str(int(time.time()))
        payload = f"{method}\n{path}\n{body}\n{timestamp}"
        signature = hmac.new(
            self.api_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'X-Signature': f'sha256={signature}',
            'X-Timestamp': timestamp
        }
    
    def process_payment(self, payment_data):
        path = '/payments/process'
        body = json.dumps(payment_data)
        
        headers = {}
        if self.api_secret:
            headers.update(self._sign_request('POST', path, body))
        
        response = self.session.post(
            f"{self.base_url}{path}",
            data=body,
            headers=headers
        )
        return response.json()

# Usage
client = PaymentAPIClient('ak_prod_your_key_here')
result = client.process_payment({
    'amount': 99.99,
    'currency': 'USD',
    'payment_method': 'card',
    'customer_id': 'cust_123'
})
```

### Node.js Integration

```javascript
const axios = require('axios');
const crypto = require('crypto');

class PaymentAPIClient {
  constructor(apiKey, baseURL = 'https://api.portal.dev/marketplace/v1', apiSecret = null) {
    this.apiKey = apiKey;
    this.baseURL = baseURL;
    this.apiSecret = apiSecret;
    
    this.client = axios.create({
      baseURL: this.baseURL,
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
        'User-Agent': 'PaymentClient/1.0'
      }
    });
  }
  
  signRequest(method, path, body) {
    if (!this.apiSecret) return {};
    
    const timestamp = Math.floor(Date.now() / 1000);
    const payload = `${method}\n${path}\n${body}\n${timestamp}`;
    const signature = crypto
      .createHmac('sha256', this.apiSecret)
      .update(payload)
      .digest('hex');
    
    return {
      'X-Signature': `sha256=${signature}`,
      'X-Timestamp': timestamp
    };
  }
  
  async processPayment(paymentData) {
    const path = '/payments/process';
    const body = JSON.stringify(paymentData);
    
    const headers = this.signRequest('POST', path, body);
    
    try {
      const response = await this.client.post(path, paymentData, { headers });
      return response.data;
    } catch (error) {
      throw new Error(`Payment processing failed: ${error.response?.data?.error?.message || error.message}`);
    }
  }
}

// Usage
const client = new PaymentAPIClient('ak_prod_your_key_here');
const result = await client.processPayment({
  amount: 99.99,
  currency: 'USD',
  payment_method: 'card',
  customer_id: 'cust_123'
});
```

## Security Best Practices

### API Key Management
1. **Environment Variables**: Store API keys in environment variables, never in code
2. **Key Rotation**: Regularly rotate API keys using the lifecycle management system
3. **Scope Limitation**: Use minimal required scopes for each API key
4. **Monitoring**: Monitor API key usage through the analytics dashboard

### Network Security
1. **HTTPS Only**: All API calls must use HTTPS encryption
2. **IP Whitelisting**: Restrict API key access to known IP addresses
3. **Request Signing**: Use HMAC signing for sensitive operations
4. **Timeout Handling**: Implement proper timeout and retry logic

### Data Protection
1. **No Sensitive Data**: Never log API keys or payment data
2. **Tokenization**: Use payment tokens instead of raw card data
3. **Data Minimization**: Only request necessary data fields
4. **Compliance**: Follow PCI DSS guidelines even in mock environment

## Monitoring & Analytics

### Real-time Monitoring
- API key usage tracking through existing dashboard
- Rate limit monitoring and alerting
- Error rate and performance metrics
- Security event logging and notifications

### Compliance Reporting
- Payment transaction audit logs
- API access and authentication logs
- Rate limiting and security incident reports
- Usage analytics for regulatory compliance

---

*For additional support with authentication setup or troubleshooting, consult the main API Developer Portal documentation or contact the development team.*