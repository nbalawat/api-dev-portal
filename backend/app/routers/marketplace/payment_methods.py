"""
Payment Method Management API - Secure storage and management of customer payment methods.

This module provides comprehensive payment method management including tokenization,
storage, updating, and secure handling of sensitive payment data.
"""

import uuid
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies.database import get_database
from ...middleware import require_api_key
from ...middleware.permissions import require_resource_permission
from ...core.permissions import ResourceType, Permission
from ...models.api_key import APIKey

router = APIRouter(prefix="/v1/payment-methods", tags=["Payment Method Management"])

# Payment Method Models

class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    DIGITAL_WALLET = "digital_wallet"
    ACH = "ach"
    WIRE = "wire"

class CardBrand(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMERICAN_EXPRESS = "amex"
    DISCOVER = "discover"
    DINERS_CLUB = "diners_club"
    JCB = "jcb"
    UNIONPAY = "unionpay"

class PaymentMethodStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    VERIFICATION_REQUIRED = "verification_required"
    FAILED_VERIFICATION = "failed_verification"

class BillingDetails(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None

class CardDetails(BaseModel):
    brand: CardBrand
    last4: str
    exp_month: int
    exp_year: int
    funding: str = "credit"
    country: str = "US"
    fingerprint: str
    cvc_check: Optional[str] = "pass"

class BankAccountDetails(BaseModel):
    last4: str
    routing_number: str
    account_type: str
    bank_name: str
    country: str = "US"
    fingerprint: str
    status: str = "verified"

class DigitalWalletDetails(BaseModel):
    provider: str
    email: Optional[str] = None
    verified: bool = True

class CreateCardRequest(BaseModel):
    number: str = Field(..., min_length=13, max_length=19)
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2024, le=2040)
    cvc: str = Field(..., min_length=3, max_length=4)
    name: Optional[str] = None
    
    @validator('number')
    def validate_card_number(cls, v):
        v = v.replace(' ', '').replace('-', '')
        if not v.isdigit():
            raise ValueError('Card number must contain only digits')
        return v

class CreateBankAccountRequest(BaseModel):
    account_number: str = Field(..., min_length=4, max_length=17)
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_holder_name: str
    account_type: str = Field(default="checking")

class CreateDigitalWalletRequest(BaseModel):
    provider: str = Field(..., pattern="^(paypal|apple_pay|google_pay|samsung_pay)$")
    email: Optional[str] = None

class CreatePaymentMethodRequest(BaseModel):
    type: PaymentMethodType
    customer_id: str
    card: Optional[CreateCardRequest] = None
    bank_account: Optional[CreateBankAccountRequest] = None
    digital_wallet: Optional[CreateDigitalWalletRequest] = None
    billing_details: Optional[BillingDetails] = None
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class UpdatePaymentMethodRequest(BaseModel):
    billing_details: Optional[BillingDetails] = None
    metadata: Optional[Dict[str, str]] = None
    card: Optional[Dict[str, Any]] = None  # Limited card updates (exp_month, exp_year, name)

class PaymentMethodResponse(BaseModel):
    id: str
    object: str = "payment_method"
    type: PaymentMethodType
    customer_id: str
    status: PaymentMethodStatus
    card: Optional[CardDetails] = None
    bank_account: Optional[BankAccountDetails] = None
    digital_wallet: Optional[DigitalWalletDetails] = None
    billing_details: Optional[BillingDetails] = None
    created: int
    updated: int
    metadata: Dict[str, str]

class PaymentMethodListResponse(BaseModel):
    object: str = "list"
    data: List[PaymentMethodResponse]
    has_more: bool
    total_count: int
    url: str

# Mock Payment Method Processing

class MockPaymentMethodProcessor:
    
    @staticmethod
    def get_card_brand(card_number: str) -> CardBrand:
        """Determine card brand from card number."""
        first_digit = card_number[0]
        first_two = card_number[:2]
        first_four = card_number[:4]
        
        if first_digit == '4':
            return CardBrand.VISA
        elif first_two in ['51', '52', '53', '54', '55'] or 2221 <= int(first_four) <= 2720:
            return CardBrand.MASTERCARD
        elif first_two in ['34', '37']:
            return CardBrand.AMERICAN_EXPRESS
        elif first_four in ['6011'] or first_two == '65':
            return CardBrand.DISCOVER
        elif first_two in ['30', '36', '38']:
            return CardBrand.DINERS_CLUB
        elif first_four in ['3528', '3589']:
            return CardBrand.JCB
        elif first_two == '62':
            return CardBrand.UNIONPAY
        else:
            return CardBrand.VISA
    
    @staticmethod
    def generate_fingerprint(data: str) -> str:
        """Generate a unique fingerprint for the payment method."""
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    @staticmethod
    def should_fail_verification(payment_method_type: PaymentMethodType, data: Any) -> tuple[bool, PaymentMethodStatus]:
        """Determine if payment method verification should fail."""
        
        # Test scenarios for verification failures
        import random
        
        if payment_method_type == PaymentMethodType.CARD:
            # Check for specific test cards that require verification
            if hasattr(data, 'number'):
                if data.number in ["4000000000000101", "4000000000000333"]:
                    return True, PaymentMethodStatus.VERIFICATION_REQUIRED
                elif data.number == "4000000000000341":
                    return True, PaymentMethodStatus.FAILED_VERIFICATION
        
        elif payment_method_type == PaymentMethodType.BANK_ACCOUNT:
            # Random verification requirement for bank accounts (10%)
            if random.random() < 0.1:
                return True, PaymentMethodStatus.VERIFICATION_REQUIRED
        
        # Random failure for realistic behavior (2%)
        if random.random() < 0.02:
            return True, PaymentMethodStatus.FAILED_VERIFICATION
        
        return False, PaymentMethodStatus.ACTIVE
    
    @staticmethod
    def create_payment_method(request: CreatePaymentMethodRequest) -> PaymentMethodResponse:
        """Create a new payment method."""
        
        pm_id = f"pm_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Determine verification status
        verification_failed, status = MockPaymentMethodProcessor.should_fail_verification(
            request.type, request.card or request.bank_account or request.digital_wallet
        )
        
        # Create response based on type
        if request.type == PaymentMethodType.CARD and request.card:
            brand = MockPaymentMethodProcessor.get_card_brand(request.card.number)
            last4 = request.card.number[-4:]
            fingerprint = MockPaymentMethodProcessor.generate_fingerprint(f"card_{request.card.number}")
            
            card_details = CardDetails(
                brand=brand,
                last4=last4,
                exp_month=request.card.exp_month,
                exp_year=request.card.exp_year,
                fingerprint=fingerprint,
                cvc_check="pass" if status == PaymentMethodStatus.ACTIVE else "fail"
            )
            
            return PaymentMethodResponse(
                id=pm_id,
                type=request.type,
                customer_id=request.customer_id,
                status=status,
                card=card_details,
                billing_details=request.billing_details,
                created=current_time,
                updated=current_time,
                metadata=request.metadata or {}
            )
        
        elif request.type == PaymentMethodType.BANK_ACCOUNT and request.bank_account:
            last4 = request.bank_account.account_number[-4:]
            fingerprint = MockPaymentMethodProcessor.generate_fingerprint(f"bank_{request.bank_account.account_number}")
            
            # Mock bank name lookup
            bank_names = {
                "021000021": "Chase Bank",
                "111000025": "Wells Fargo",
                "121000248": "Bank of America",
                "011401533": "PNC Bank",
                "054001204": "Citibank"
            }
            
            bank_name = bank_names.get(request.bank_account.routing_number, "Unknown Bank")
            
            bank_details = BankAccountDetails(
                last4=last4,
                routing_number=request.bank_account.routing_number,
                account_type=request.bank_account.account_type,
                bank_name=bank_name,
                fingerprint=fingerprint,
                status="verified" if status == PaymentMethodStatus.ACTIVE else "verification_required"
            )
            
            return PaymentMethodResponse(
                id=pm_id,
                type=request.type,
                customer_id=request.customer_id,
                status=status,
                bank_account=bank_details,
                billing_details=request.billing_details,
                created=current_time,
                updated=current_time,
                metadata=request.metadata or {}
            )
        
        elif request.type == PaymentMethodType.DIGITAL_WALLET and request.digital_wallet:
            wallet_details = DigitalWalletDetails(
                provider=request.digital_wallet.provider,
                email=request.digital_wallet.email,
                verified=status == PaymentMethodStatus.ACTIVE
            )
            
            return PaymentMethodResponse(
                id=pm_id,
                type=request.type,
                customer_id=request.customer_id,
                status=status,
                digital_wallet=wallet_details,
                billing_details=request.billing_details,
                created=current_time,
                updated=current_time,
                metadata=request.metadata or {}
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment method type or missing required data"
            )

# In-memory storage for demo purposes
MOCK_PAYMENT_METHODS: Dict[str, PaymentMethodResponse] = {}

# API Endpoints

@router.post("/create", response_model=PaymentMethodResponse)
async def create_payment_method(
    pm_request: CreatePaymentMethodRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.CREATE))
):
    """
    Create a new payment method.
    
    This endpoint securely stores a customer's payment method with tokenization
    and supports cards, bank accounts, and digital wallets.
    """
    
    payment_method = MockPaymentMethodProcessor.create_payment_method(pm_request)
    
    # Store in mock database
    MOCK_PAYMENT_METHODS[payment_method.id] = payment_method
    
    return payment_method

@router.get("/{pm_id}", response_model=PaymentMethodResponse)
async def get_payment_method(
    pm_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    Retrieve a specific payment method by ID.
    
    Returns payment method details without sensitive information.
    """
    
    if pm_id not in MOCK_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    return MOCK_PAYMENT_METHODS[pm_id]

@router.post("/{pm_id}/update", response_model=PaymentMethodResponse)
async def update_payment_method(
    pm_id: str,
    update_request: UpdatePaymentMethodRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.UPDATE))
):
    """
    Update a payment method.
    
    Allows updating billing details, metadata, and limited card information
    like expiration dates.
    """
    
    if pm_id not in MOCK_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    payment_method = MOCK_PAYMENT_METHODS[pm_id]
    
    # Update billing details
    if update_request.billing_details:
        payment_method.billing_details = update_request.billing_details
    
    # Update metadata
    if update_request.metadata:
        payment_method.metadata.update(update_request.metadata)
    
    # Update card details (limited)
    if update_request.card and payment_method.card:
        if "exp_month" in update_request.card:
            payment_method.card.exp_month = update_request.card["exp_month"]
        if "exp_year" in update_request.card:
            payment_method.card.exp_year = update_request.card["exp_year"]
    
    payment_method.updated = int(time.time())
    
    return payment_method

@router.delete("/{pm_id}")
async def delete_payment_method(
    pm_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.DELETE))
):
    """
    Delete a payment method.
    
    Permanently removes the payment method from the customer's account.
    This action cannot be undone.
    """
    
    if pm_id not in MOCK_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    del MOCK_PAYMENT_METHODS[pm_id]
    
    return {"deleted": True, "id": pm_id}

@router.get("/customers/{customer_id}/list", response_model=PaymentMethodListResponse)
async def list_customer_payment_methods(
    customer_id: str,
    limit: int = Query(25, ge=1, le=100),
    payment_method_type: Optional[PaymentMethodType] = Query(None),
    status: Optional[PaymentMethodStatus] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    List payment methods for a specific customer.
    
    Returns all payment methods associated with a customer with optional
    filtering by type and status.
    """
    
    # Filter by customer
    payment_methods = [
        pm for pm in MOCK_PAYMENT_METHODS.values()
        if pm.customer_id == customer_id
    ]
    
    # Apply filters
    if payment_method_type:
        payment_methods = [pm for pm in payment_methods if pm.type == payment_method_type]
    
    if status:
        payment_methods = [pm for pm in payment_methods if pm.status == status]
    
    # Sort by creation time (newest first)
    payment_methods.sort(key=lambda x: x.created, reverse=True)
    
    # Apply limit
    paginated_payment_methods = payment_methods[:limit]
    has_more = len(payment_methods) > limit
    
    return PaymentMethodListResponse(
        data=paginated_payment_methods,
        has_more=has_more,
        total_count=len(payment_methods),
        url=f"/marketplace/v1/payment-methods/customers/{customer_id}/list"
    )

@router.post("/{pm_id}/verify")
async def verify_payment_method(
    pm_id: str,
    verification_data: Optional[Dict[str, Any]] = None,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.UPDATE))
):
    """
    Verify a payment method.
    
    This endpoint is used to complete verification for payment methods that
    require additional verification steps (like micro-deposits for bank accounts).
    """
    
    if pm_id not in MOCK_PAYMENT_METHODS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found"
        )
    
    payment_method = MOCK_PAYMENT_METHODS[pm_id]
    
    if payment_method.status != PaymentMethodStatus.VERIFICATION_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment method does not require verification"
        )
    
    # Mock verification logic
    import random
    verification_success = random.random() > 0.1  # 90% success rate
    
    if verification_success:
        payment_method.status = PaymentMethodStatus.ACTIVE
        if payment_method.bank_account:
            payment_method.bank_account.status = "verified"
    else:
        payment_method.status = PaymentMethodStatus.FAILED_VERIFICATION
    
    payment_method.updated = int(time.time())
    
    return {
        "payment_method_id": pm_id,
        "verification_status": payment_method.status.value,
        "verified": verification_success
    }

@router.get("/analytics/summary")
async def get_payment_method_analytics(
    customer_id: Optional[str] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    Get payment method analytics and statistics.
    
    Returns comprehensive metrics about stored payment methods including
    type distribution, status breakdown, and trends.
    """
    
    payment_methods = list(MOCK_PAYMENT_METHODS.values())
    
    if customer_id:
        payment_methods = [pm for pm in payment_methods if pm.customer_id == customer_id]
    
    # Calculate metrics
    total_payment_methods = len(payment_methods)
    
    # Type distribution
    type_distribution = {}
    for pm_type in PaymentMethodType:
        type_count = len([pm for pm in payment_methods if pm.type == pm_type])
        type_distribution[pm_type.value] = type_count
    
    # Status distribution
    status_distribution = {}
    for pm_status in PaymentMethodStatus:
        status_count = len([pm for pm in payment_methods if pm.status == pm_status])
        status_distribution[pm_status.value] = status_count
    
    # Card brand distribution
    card_brand_distribution = {}
    card_methods = [pm for pm in payment_methods if pm.type == PaymentMethodType.CARD and pm.card]
    for card_pm in card_methods:
        brand = card_pm.card.brand.value
        card_brand_distribution[brand] = card_brand_distribution.get(brand, 0) + 1
    
    # Active vs inactive
    active_count = len([pm for pm in payment_methods if pm.status == PaymentMethodStatus.ACTIVE])
    active_rate = (active_count / total_payment_methods * 100) if total_payment_methods > 0 else 0
    
    return {
        "total_payment_methods": total_payment_methods,
        "active_payment_methods": active_count,
        "active_rate_percent": round(active_rate, 2),
        "type_distribution": type_distribution,
        "status_distribution": status_distribution,
        "card_brand_distribution": card_brand_distribution,
        "verification_metrics": {
            "requiring_verification": status_distribution.get("verification_required", 0),
            "failed_verification": status_distribution.get("failed_verification", 0),
            "verification_success_rate": "90%" # Mock rate
        }
    }

# Health check endpoint
@router.get("/health")
async def payment_method_api_health():
    """Health check for payment method management API."""
    return {
        "status": "healthy",
        "service": "payment_method_management",
        "version": "1.0.0",
        "endpoints": [
            "POST /create",
            "GET /{pm_id}",
            "POST /{pm_id}/update",
            "DELETE /{pm_id}",
            "GET /customers/{customer_id}/list",
            "POST /{pm_id}/verify",
            "GET /analytics/summary"
        ],
        "mock_features": [
            "Secure tokenization",
            "Multiple payment method types",
            "Verification workflows",
            "Billing details management",
            "Analytics and reporting"
        ],
        "supported_types": [t.value for t in PaymentMethodType]
    }