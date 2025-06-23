# Phase 1 Testing Guide - Core Payment Processing APIs

## Overview

This document provides comprehensive testing instructions for Phase 1 of the Mock Payment Ecosystem, which includes 5 core payment processing APIs:

1. **Payment Processing API** - Process payments, authorizations, captures, and voids
2. **Refund Management API** - Handle full and partial refunds with tracking
3. **Subscription Billing API** - Recurring payment management with flexible billing
4. **Transaction History API** - Advanced transaction querying and reporting
5. **Payment Method Management API** - Secure storage and management of payment methods

## Prerequisites

### 1. Environment Setup
- Backend running in Docker at `http://localhost:8000`
- Valid API key with payment permissions

### 2. API Key Creation
```bash
# Step 1: Login to get admin token
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=admin@example.com&password=admin123'

# Step 2: Create API key with admin scope (includes payment permissions)
curl -X POST "http://localhost:8000/api/api-keys/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "name": "Payment Test Key",
    "scopes": ["admin"],
    "rate_limit": 1000,
    "rate_limit_period": "requests_per_hour"
  }'

# Save the returned secret_key for testing
export API_KEY="sk_YOUR_SECRET_KEY_HERE"
```

## API Testing Instructions

### 1. Payment Processing API

#### Health Check
```bash
curl "http://localhost:8000/marketplace/v1/payments/health" \
  -H "X-API-Key: $API_KEY"
```

#### Process a Payment
```bash
curl -X POST "http://localhost:8000/marketplace/v1/payments/process" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 29.99,
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
    "customer_id": "cust_test_123",
    "description": "Test payment"
  }'
```

#### Test Payment Failure Scenarios
```bash
# Declined card
curl -X POST "http://localhost:8000/marketplace/v1/payments/process" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 29.99,
    "currency": "USD",
    "payment_method": {
      "type": "card",
      "card": {
        "number": "4000000000000002",
        "exp_month": 12,
        "exp_year": 2025,
        "cvc": "123"
      }
    },
    "customer_id": "cust_test_123",
    "description": "Test declined payment"
  }'

# Insufficient funds
curl -X POST "http://localhost:8000/marketplace/v1/payments/process" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 29.99,
    "currency": "USD",
    "payment_method": {
      "type": "card",
      "card": {
        "number": "4000000000009995",
        "exp_month": 12,
        "exp_year": 2025,
        "cvc": "123"
      }
    },
    "customer_id": "cust_test_123",
    "description": "Test insufficient funds"
  }'
```

#### Authorize and Capture
```bash
# Authorize payment
curl -X POST "http://localhost:8000/marketplace/v1/payments/authorize" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00,
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
    "customer_id": "cust_test_123",
    "description": "Test authorization"
  }'

# Capture the authorized payment (use payment ID from above response)
curl -X POST "http://localhost:8000/marketplace/v1/payments/PAYMENT_ID/capture" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 50.00
  }'
```

#### Retrieve Payment
```bash
curl "http://localhost:8000/marketplace/v1/payments/PAYMENT_ID" \
  -H "X-API-Key: $API_KEY"
```

#### List Payments
```bash
curl "http://localhost:8000/marketplace/v1/payments/?limit=10" \
  -H "X-API-Key: $API_KEY"
```

### 2. Refund Management API

#### Create Full Refund
```bash
curl -X POST "http://localhost:8000/marketplace/v1/refunds/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "PAYMENT_ID",
    "reason": "requested_by_customer"
  }'
```

#### Create Partial Refund
```bash
curl -X POST "http://localhost:8000/marketplace/v1/refunds/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "PAYMENT_ID",
    "amount": 10.00,
    "reason": "product_unacceptable",
    "metadata": {
      "support_ticket": "TK-12345"
    }
  }'
```

#### Retrieve Refund
```bash
curl "http://localhost:8000/marketplace/v1/refunds/REFUND_ID" \
  -H "X-API-Key: $API_KEY"
```

#### List Refunds
```bash
curl "http://localhost:8000/marketplace/v1/refunds/?limit=10" \
  -H "X-API-Key: $API_KEY"
```

#### Refund Analytics
```bash
curl "http://localhost:8000/marketplace/v1/refunds/analytics/summary?days=30" \
  -H "X-API-Key: $API_KEY"
```

### 3. Subscription Billing API

#### List Available Plans
```bash
curl "http://localhost:8000/marketplace/v1/subscriptions/plans/list" \
  -H "X-API-Key: $API_KEY"
```

#### Create Subscription
```bash
curl -X POST "http://localhost:8000/marketplace/v1/subscriptions/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_test_123",
    "plan_id": "plan_premium_monthly",
    "payment_method_id": "pm_test_123",
    "trial_period_days": 14,
    "metadata": {
      "signup_source": "website"
    }
  }'
```

#### Update Subscription
```bash
curl -X POST "http://localhost:8000/marketplace/v1/subscriptions/SUBSCRIPTION_ID/update" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_enterprise_monthly",
    "proration_behavior": "create_prorations"
  }'
```

#### Cancel Subscription
```bash
curl -X POST "http://localhost:8000/marketplace/v1/subscriptions/SUBSCRIPTION_ID/cancel" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "cancel_at_period_end": true,
    "reason": "user_requested"
  }'
```

#### Get Subscription Invoices
```bash
curl "http://localhost:8000/marketplace/v1/subscriptions/SUBSCRIPTION_ID/invoices" \
  -H "X-API-Key: $API_KEY"
```

### 4. Transaction History API

#### List All Transactions
```bash
curl "http://localhost:8000/marketplace/v1/transactions/list?limit=25" \
  -H "X-API-Key: $API_KEY"
```

#### Filter Transactions
```bash
# By customer
curl "http://localhost:8000/marketplace/v1/transactions/list?customer_id=cust_test_123" \
  -H "X-API-Key: $API_KEY"

# By transaction type
curl "http://localhost:8000/marketplace/v1/transactions/list?transaction_type=payment" \
  -H "X-API-Key: $API_KEY"

# By date range
curl "http://localhost:8000/marketplace/v1/transactions/list?date_from=2024-01-01&date_to=2024-12-31" \
  -H "X-API-Key: $API_KEY"
```

#### Search Transactions
```bash
curl -X POST "http://localhost:8000/marketplace/v1/transactions/search" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test payment",
    "amount_min": 10.00,
    "amount_max": 100.00
  }'
```

#### Transaction Analytics
```bash
curl "http://localhost:8000/marketplace/v1/transactions/analytics/summary?days=30" \
  -H "X-API-Key: $API_KEY"
```

#### Export Transaction Data
```bash
# JSON export
curl "http://localhost:8000/marketplace/v1/transactions/export/json" \
  -H "X-API-Key: $API_KEY" \
  -o transactions.json

# CSV export
curl "http://localhost:8000/marketplace/v1/transactions/export/csv" \
  -H "X-API-Key: $API_KEY" \
  -o transactions.csv
```

### 5. Payment Method Management API

#### Create Payment Method (Card)
```bash
curl -X POST "http://localhost:8000/marketplace/v1/payment-methods/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "card",
    "customer_id": "cust_test_123",
    "card": {
      "number": "4111111111111111",
      "exp_month": 12,
      "exp_year": 2026,
      "cvc": "123",
      "name": "John Doe"
    },
    "billing_details": {
      "name": "John Doe",
      "email": "john@example.com",
      "phone": "+1-555-123-4567"
    }
  }'
```

#### Create Payment Method (Bank Account)
```bash
curl -X POST "http://localhost:8000/marketplace/v1/payment-methods/create" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "bank_account",
    "customer_id": "cust_test_123",
    "bank_account": {
      "account_number": "123456789",
      "routing_number": "021000021",
      "account_holder_name": "John Doe",
      "account_type": "checking"
    },
    "billing_details": {
      "name": "John Doe",
      "email": "john@example.com"
    }
  }'
```

#### Update Payment Method
```bash
curl -X POST "http://localhost:8000/marketplace/v1/payment-methods/PM_ID/update" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "billing_details": {
      "name": "John Updated Doe",
      "email": "john.updated@example.com"
    },
    "card": {
      "exp_month": 6,
      "exp_year": 2027
    }
  }'
```

#### List Customer Payment Methods
```bash
curl "http://localhost:8000/marketplace/v1/payment-methods/customers/cust_test_123/list" \
  -H "X-API-Key: $API_KEY"
```

#### Verify Payment Method
```bash
curl -X POST "http://localhost:8000/marketplace/v1/payment-methods/PM_ID/verify" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "verification_code": "12"
  }'
```

#### Payment Method Analytics
```bash
curl "http://localhost:8000/marketplace/v1/payment-methods/analytics/summary" \
  -H "X-API-Key: $API_KEY"
```

## Test Scenarios & Expected Results

### Success Scenarios

| Test Case | Expected Result |
|-----------|----------------|
| Process payment with valid Visa card (4111111111111111) | `status: "succeeded"` |
| Create partial refund for successful payment | `status: "succeeded"`, correct amount |
| Subscribe to monthly plan with trial | `status: "trialing"`, trial_end set |
| List transactions with filters | Filtered results matching criteria |
| Store card payment method | `status: "active"`, last4 masked |

### Failure Scenarios

| Test Case | Expected Result |
|-----------|----------------|
| Process payment with declined card (4000000000000002) | `status: "failed"`, `failure_code: "card_declined"` |
| Process payment with insufficient funds (4000000000009995) | `status: "failed"`, `failure_code: "insufficient_funds"` |
| Create refund for non-existent payment | `404 Not Found` |
| Access endpoint without API key | `401 Unauthorized` |
| Access endpoint with insufficient permissions | `403 Forbidden` |

### Performance & Rate Limiting

#### Test Rate Limits
```bash
# Rapid fire requests to test rate limiting
for i in {1..50}; do
  curl -w "\n%{http_code} " "http://localhost:8000/marketplace/v1/payments/health" \
    -H "X-API-Key: $API_KEY"
done
```

#### Expected Rate Limit Headers
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
X-RateLimit-Algorithm: token-bucket
```

## Integration Workflows

### Complete E-commerce Checkout Flow
1. Create payment method for customer
2. Process payment using stored payment method
3. Handle success/failure scenarios
4. Process refund if needed
5. Track all transactions

### Subscription Management Flow
1. List available subscription plans
2. Create subscription with trial period
3. Handle first payment after trial
4. Update subscription (upgrade/downgrade)
5. Cancel subscription with proper timing

### Marketplace Payout Flow
1. Process multiple payments from different customers
2. Calculate fees and net amounts
3. Generate transaction reports
4. Export data for reconciliation

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check API key format (should start with `sk_`)
   - Verify API key is active and not expired
   - Ensure request includes `X-API-Key` header

2. **403 Forbidden**
   - Check API key has required payment scopes
   - Admin scope includes all payment permissions
   - Create new API key with `admin` scope if needed

3. **404 Not Found**
   - Verify correct endpoint URLs
   - Check if backend is running on port 8000
   - Ensure marketplace APIs are properly mounted

4. **422 Validation Error**
   - Check request body format and required fields
   - Verify card number format (13-19 digits)
   - Ensure currency is 3-letter ISO code (USD, EUR, etc.)

### Debugging Tips

1. **Enable Verbose Logging**
   ```bash
   curl -v "http://localhost:8000/marketplace/v1/payments/health" \
     -H "X-API-Key: $API_KEY"
   ```

2. **Check Backend Logs**
   ```bash
   docker-compose logs backend | tail -50
   ```

3. **Validate JSON Payloads**
   Use tools like `jq` to validate JSON format:
   ```bash
   echo '{"amount": 29.99}' | jq .
   ```

## Test Data Reference

### Test Credit Cards
- **Visa Success**: 4111111111111111
- **Visa Declined**: 4000000000000002  
- **Visa Insufficient Funds**: 4000000000009995
- **Mastercard Success**: 5555555555554444
- **Amex Success**: 378282246310005

### Test Bank Accounts
- **Valid Routing**: 021000021 (Chase)
- **Valid Account**: 123456789
- **Invalid Routing**: 111000025

### Sample Customer IDs
- `cust_test_123`
- `cust_demo_456`
- `cust_enterprise_789`

## Summary

Phase 1 of the Mock Payment Ecosystem provides a solid foundation with 5 core APIs that handle the complete payment lifecycle:

✅ **Payment Processing** - Multiple payment methods, realistic success/failure rates
✅ **Refund Management** - Full/partial refunds with comprehensive tracking
✅ **Subscription Billing** - Flexible recurring payments with trial periods
✅ **Transaction History** - Advanced querying, filtering, and analytics
✅ **Payment Method Management** - Secure tokenization and storage

All APIs support realistic test scenarios, proper error handling, rate limiting, and comprehensive documentation. The system is ready for integration testing and development of higher-level payment workflows.

**Next Steps**: Proceed to Phase 2 (Financial Services APIs) for bank verification, currency exchange, credit scoring, and financial reporting capabilities.