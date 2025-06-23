# Payment API Catalog - Complete Reference

## API Overview

The Mock Payment Ecosystem provides 16 comprehensive APIs organized into 4 functional categories. Each API includes realistic endpoints, data models, and error handling to simulate a production payment platform.

---

## Phase 1: Core Payment Processing (5 APIs)

### 1. Payment Processing API
**Base Path**: `/marketplace/v1/payments`
**Required Scope**: `payment:write`

Process various payment types including credit cards, bank transfers, and digital wallets.

#### Key Endpoints

```http
POST /payments/process
POST /payments/authorize
POST /payments/capture
POST /payments/void
GET  /payments/{payment_id}
```

#### Example: Process Payment
```bash
curl -X POST https://api.portal.dev/marketplace/v1/payments/process \
  -H 'X-API-Key: ak_prod_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": 99.99,
    "currency": "USD",
    "payment_method": {
      "type": "card",
      "card": {
        "number": "4111111111111111",
        "exp_month": 12,
        "exp_year": 2025,
        "cvc": "123"
      }
    },
    "customer_id": "cust_12345",
    "description": "Product purchase",
    "metadata": {
      "order_id": "order_67890",
      "product_name": "Premium Subscription"
    }
  }'
```

#### Response
```json
{
  "id": "pay_1234567890",
  "status": "succeeded",
  "amount": 99.99,
  "currency": "usd",
  "payment_method": {
    "type": "card",
    "card": {
      "brand": "visa",
      "last4": "1111",
      "exp_month": 12,
      "exp_year": 2025
    }
  },
  "customer_id": "cust_12345",
  "created": 1704067200,
  "transaction_id": "txn_abcdef123456",
  "receipt_url": "https://api.portal.dev/receipts/pay_1234567890"
}
```

### 2. Refund Management API
**Base Path**: `/marketplace/v1/refunds`
**Required Scope**: `payment:write`

Handle full and partial refunds with comprehensive tracking.

#### Key Endpoints
```http
POST /refunds/create
GET  /refunds/{refund_id}
GET  /refunds/list
POST /refunds/{refund_id}/cancel
```

#### Example: Create Refund
```bash
curl -X POST https://api.portal.dev/marketplace/v1/refunds/create \
  -H 'X-API-Key: ak_prod_...' \
  -d '{
    "payment_id": "pay_1234567890",
    "amount": 49.99,
    "reason": "customer_request",
    "metadata": {
      "support_ticket": "TK-12345"
    }
  }'
```

### 3. Subscription Billing API
**Base Path**: `/marketplace/v1/subscriptions`
**Required Scope**: `payment:write`

Manage recurring payments, billing cycles, and subscription lifecycle.

#### Key Endpoints
```http
POST /subscriptions/create
GET  /subscriptions/{subscription_id}
POST /subscriptions/{subscription_id}/update
POST /subscriptions/{subscription_id}/cancel
GET  /subscriptions/{subscription_id}/invoices
```

#### Example: Create Subscription
```bash
curl -X POST https://api.portal.dev/marketplace/v1/subscriptions/create \
  -H 'X-API-Key: ak_prod_...' \
  -d '{
    "customer_id": "cust_12345",
    "plan_id": "plan_premium_monthly",
    "payment_method_id": "pm_card_visa_1111",
    "billing_cycle_anchor": "2024-01-01",
    "proration_behavior": "create_prorations"
  }'
```

### 4. Transaction History API
**Base Path**: `/marketplace/v1/transactions`
**Required Scope**: `payment:read`

Query payment history with advanced filtering and reporting capabilities.

#### Key Endpoints
```http
GET /transactions/list
GET /transactions/{transaction_id}
GET /transactions/search
GET /transactions/export
GET /transactions/analytics
```

#### Example: List Transactions
```bash
curl -X GET 'https://api.portal.dev/marketplace/v1/transactions/list?limit=25&status=succeeded&date_from=2024-01-01' \
  -H 'X-API-Key: ak_prod_...'
```

### 5. Payment Method Management API
**Base Path**: `/marketplace/v1/payment-methods`
**Required Scope**: `payment:write`

Securely store and manage customer payment methods.

#### Key Endpoints
```http
POST /payment-methods/create
GET  /payment-methods/{pm_id}
POST /payment-methods/{pm_id}/update
DELETE /payment-methods/{pm_id}
GET  /customers/{customer_id}/payment-methods
```

---

## Phase 2: Financial Services (4 APIs)

### 6. Bank Account Verification API
**Base Path**: `/marketplace/v1/bank-verification`
**Required Scope**: `payment:admin`

Verify bank accounts through micro-deposits and instant verification.

#### Key Endpoints
```http
POST /bank-verification/initiate
POST /bank-verification/confirm
GET  /bank-verification/{verification_id}
POST /bank-verification/instant
```

#### Example: Instant Verification
```bash
curl -X POST https://api.portal.dev/marketplace/v1/bank-verification/instant \
  -H 'X-API-Key: ak_prod_...' \
  -d '{
    "account_number": "123456789",
    "routing_number": "021000021",
    "account_type": "checking",
    "account_holder_name": "John Doe"
  }'
```

### 7. Currency Exchange API
**Base Path**: `/marketplace/v1/fx`
**Required Scope**: `payment:read`

Real-time currency conversion with competitive exchange rates.

#### Key Endpoints
```http
GET /fx/rates
GET /fx/rates/{from}/{to}
POST /fx/convert
GET /fx/history
```

#### Example: Get Exchange Rate
```bash
curl -X GET 'https://api.portal.dev/marketplace/v1/fx/rates/USD/EUR' \
  -H 'X-API-Key: ak_prod_...'
```

### 8. Credit Scoring API
**Base Path**: `/marketplace/v1/credit`
**Required Scope**: `payment:compliance`

Assess credit risk and make lending decisions.

#### Key Endpoints
```http
POST /credit/score
GET  /credit/report/{customer_id}
POST /credit/decision
GET  /credit/history/{customer_id}
```

### 9. Financial Reporting API
**Base Path**: `/marketplace/v1/reporting`
**Required Scope**: `payment:admin`

Generate comprehensive financial reports and analytics.

#### Key Endpoints
```http
GET /reporting/revenue
GET /reporting/reconciliation
GET /reporting/tax-summary
POST /reporting/custom
```

---

## Phase 3: Security & Compliance (4 APIs)

### 10. Fraud Detection API
**Base Path**: `/marketplace/v1/fraud`
**Required Scope**: `payment:compliance`

ML-powered fraud detection and risk assessment.

#### Key Endpoints
```http
POST /fraud/analyze
GET  /fraud/score/{transaction_id}
POST /fraud/rules/create
GET  /fraud/alerts
```

#### Example: Analyze Transaction
```bash
curl -X POST https://api.portal.dev/marketplace/v1/fraud/analyze \
  -H 'X-API-Key: ak_prod_...' \
  -d '{
    "transaction_id": "txn_12345",
    "amount": 999.99,
    "currency": "USD",
    "customer": {
      "id": "cust_12345",
      "email": "customer@example.com",
      "ip_address": "192.168.1.100"
    },
    "payment_method": {
      "type": "card",
      "fingerprint": "fp_12345"
    }
  }'
```

### 11. KYC Verification API
**Base Path**: `/marketplace/v1/kyc`
**Required Scope**: `payment:compliance`

Identity verification and document validation.

#### Key Endpoints
```http
POST /kyc/verification/create
POST /kyc/documents/upload
GET  /kyc/verification/{verification_id}
POST /kyc/verification/{verification_id}/approve
```

### 12. AML Monitoring API
**Base Path**: `/marketplace/v1/aml`
**Required Scope**: `payment:compliance`

Anti-money laundering transaction monitoring.

#### Key Endpoints
```http
POST /aml/screen
GET  /aml/alerts
POST /aml/alerts/{alert_id}/investigate
GET  /aml/reports/suspicious-activity
```

### 13. Cryptocurrency API
**Base Path**: `/marketplace/v1/crypto`
**Required Scope**: `payment:write`

Process cryptocurrency payments and manage digital wallets.

#### Key Endpoints
```http
POST /crypto/wallets/create
GET  /crypto/wallets/{wallet_id}/balance
POST /crypto/payments/process
GET  /crypto/rates
```

---

## Phase 4: Marketplace Tools (3 APIs)

### 14. Vendor Payout API
**Base Path**: `/marketplace/v1/payouts`
**Required Scope**: `payment:admin`

Manage multi-party payouts and commission splits.

#### Key Endpoints
```http
POST /payouts/create
GET  /payouts/{payout_id}
POST /payouts/batch
GET  /payouts/schedule
```

#### Example: Create Vendor Payout
```bash
curl -X POST https://api.portal.dev/marketplace/v1/payouts/create \
  -H 'X-API-Key: ak_prod_...' \
  -d '{
    "vendor_id": "vendor_12345",
    "amount": 850.00,
    "currency": "USD",
    "source_transaction": "txn_original_sale",
    "payout_method": {
      "type": "bank_account",
      "account_id": "bank_acc_67890"
    },
    "metadata": {
      "commission_rate": 0.15,
      "fee_amount": 150.00
    }
  }'
```

### 15. Escrow Management API
**Base Path**: `/marketplace/v1/escrow`
**Required Scope**: `payment:admin`

Secure fund holding with milestone-based releases.

#### Key Endpoints
```http
POST /escrow/create
POST /escrow/{escrow_id}/release
POST /escrow/{escrow_id}/dispute
GET  /escrow/{escrow_id}/status
```

### 16. Digital Wallet API
**Base Path**: `/marketplace/v1/wallets`
**Required Scope**: `payment:write`

Virtual wallets with balance management and P2P transfers.

#### Key Endpoints
```http
POST /wallets/create
GET  /wallets/{wallet_id}/balance
POST /wallets/transfer
GET  /wallets/{wallet_id}/transactions
```

---

## Common Response Patterns

### Success Response
```json
{
  "id": "resource_id",
  "object": "payment|refund|subscription|etc",
  "status": "succeeded|pending|failed",
  "created": 1704067200,
  "updated": 1704067200,
  "metadata": {},
  "links": {
    "self": "https://api.portal.dev/marketplace/v1/payments/pay_123",
    "related": []
  }
}
```

### Error Response
```json
{
  "error": {
    "type": "card_error|validation_error|api_error",
    "code": "card_declined|insufficient_funds|rate_limit_exceeded",
    "message": "Human-readable error description",
    "param": "field_name_that_caused_error",
    "decline_code": "insufficient_funds"
  },
  "request_id": "req_12345"
}
```

### Pagination
```json
{
  "object": "list",
  "data": [...],
  "has_more": true,
  "total_count": 150,
  "url": "/marketplace/v1/payments/list",
  "next_page": "https://api.portal.dev/marketplace/v1/payments/list?starting_after=pay_123"
}
```

## Rate Limits by API Category

| API Category | Scope Required | Rate Limit | Burst Limit |
|-------------|----------------|------------|-------------|
| Core Payment | payment:write | 1000/hour | 100/minute |
| Financial Services | payment:read | 2000/hour | 200/minute |
| Security & Compliance | payment:compliance | 500/hour | 50/minute |
| Marketplace Tools | payment:admin | 300/hour | 30/minute |

## Testing & Validation

### Test Cards
```
Visa: 4111111111111111
Mastercard: 5555555555554444
American Express: 378282246310005
Discover: 6011111111111117

Declined Card: 4000000000000002
Insufficient Funds: 4000000000009995
Fraud Detection: 4100000000000019
```

### Test Bank Accounts
```
Valid Routing: 021000021 (Chase)
Valid Account: 123456789
Invalid Routing: 111000025
Invalid Account: 000000000
```

### Webhook Events
All APIs support webhook notifications for:
- `payment.succeeded`
- `payment.failed`
- `refund.created`
- `subscription.created`
- `fraud.alert`
- `kyc.verification.completed`

---

*This catalog provides comprehensive coverage of all 16 payment APIs. Each API includes detailed endpoint documentation, request/response examples, and integration guides in the `/marketplace/workflows/` directory.*