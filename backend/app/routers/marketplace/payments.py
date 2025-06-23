"""
Payment Processing API - Core payment operations for the mock payment ecosystem.

This module provides realistic payment processing endpoints with mock data
that simulates a production payment platform including success/failure scenarios.
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

router = APIRouter(prefix="/v1/payments", tags=["Payment Processing"])

# Payment Models

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REQUIRES_ACTION = "requires_action"

class PaymentMethodType(str, Enum):
    CARD = "card"
    BANK_ACCOUNT = "bank_account"
    DIGITAL_WALLET = "digital_wallet"
    CRYPTOCURRENCY = "cryptocurrency"

class CardBrand(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMERICAN_EXPRESS = "amex"
    DISCOVER = "discover"
    DINERS_CLUB = "diners_club"
    JCB = "jcb"
    UNIONPAY = "unionpay"

class Card(BaseModel):
    number: str = Field(..., min_length=13, max_length=19)
    exp_month: int = Field(..., ge=1, le=12)
    exp_year: int = Field(..., ge=2024, le=2040)
    cvc: str = Field(..., min_length=3, max_length=4)
    name: Optional[str] = None
    
    @validator('number')
    def validate_card_number(cls, v):
        # Remove spaces and dashes
        v = v.replace(' ', '').replace('-', '')
        if not v.isdigit():
            raise ValueError('Card number must contain only digits')
        return v

class BankAccount(BaseModel):
    account_number: str = Field(..., min_length=4, max_length=17)
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_holder_name: str
    account_type: str = Field(default="checking")

class DigitalWallet(BaseModel):
    provider: str = Field(..., pattern="^(paypal|apple_pay|google_pay|samsung_pay)$")
    wallet_id: str

class PaymentMethodInput(BaseModel):
    type: PaymentMethodType
    card: Optional[Card] = None
    bank_account: Optional[BankAccount] = None
    digital_wallet: Optional[DigitalWallet] = None

class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0, le=999999.99)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    payment_method: PaymentMethodInput
    customer_id: str
    description: Optional[str] = None
    statement_descriptor: Optional[str] = Field(None, max_length=22)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None

class AuthorizeRequest(BaseModel):
    amount: float = Field(..., gt=0, le=999999.99)
    currency: str = Field(default="USD", pattern="^[A-Z]{3}$")
    payment_method: PaymentMethodInput
    customer_id: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class CaptureRequest(BaseModel):
    amount: Optional[float] = Field(None, gt=0, le=999999.99)
    statement_descriptor: Optional[str] = Field(None, max_length=22)

# Response Models

class CardDetails(BaseModel):
    brand: CardBrand
    last4: str
    exp_month: int
    exp_year: int
    funding: str = "credit"
    country: str = "US"

class PaymentMethodResponse(BaseModel):
    type: PaymentMethodType
    card: Optional[CardDetails] = None

class PaymentResponse(BaseModel):
    id: str
    object: str = "payment"
    amount: float
    currency: str
    status: PaymentStatus
    payment_method: PaymentMethodResponse
    customer_id: str
    description: Optional[str] = None
    statement_descriptor: Optional[str] = None
    created: int
    updated: int
    transaction_id: str
    receipt_url: str
    metadata: Dict[str, str]
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None

class PaymentListResponse(BaseModel):
    object: str = "list"
    data: List[PaymentResponse]
    has_more: bool
    total_count: int
    url: str

# Mock Payment Processing Logic

class MockPaymentProcessor:
    
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
            return CardBrand.VISA  # Default fallback
    
    @staticmethod
    def should_decline_payment(card_number: str, amount: float) -> tuple[bool, Optional[str], Optional[str]]:
        """Determine if payment should be declined based on test scenarios."""
        
        # Test card numbers that always decline
        decline_cards = {
            "4000000000000002": ("card_declined", "Your card was declined."),
            "4000000000009995": ("insufficient_funds", "Your card has insufficient funds."),
            "4000000000009987": ("lost_card", "Your card has been reported lost."),
            "4000000000009979": ("stolen_card", "Your card has been reported stolen."),
            "4100000000000019": ("fraudulent", "Your card was declined due to suspicious activity."),
            "4000000000000069": ("expired_card", "Your card has expired."),
            "4000000000000127": ("incorrect_cvc", "Your card's security code is incorrect."),
        }
        
        if card_number in decline_cards:
            code, message = decline_cards[card_number]
            return True, code, message
        
        # Random decline for realistic behavior (5% decline rate)
        import random
        if random.random() < 0.05:
            return True, "card_declined", "Your card was declined."
        
        # High amount fraud detection
        if amount > 5000:
            if random.random() < 0.3:  # 30% chance of fraud alert
                return True, "fraudulent", "Transaction flagged for manual review."
        
        return False, None, None
    
    @staticmethod
    def process_payment(payment_request: PaymentRequest) -> PaymentResponse:
        """Process a payment request and return the result."""
        
        payment_id = f"pay_{uuid.uuid4().hex[:24]}"
        transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
        current_time = int(time.time())
        
        # Extract card details for processing
        if payment_request.payment_method.type == PaymentMethodType.CARD:
            card = payment_request.payment_method.card
            card_brand = MockPaymentProcessor.get_card_brand(card.number)
            last4 = card.number[-4:]
            
            # Check if payment should be declined
            should_decline, failure_code, failure_message = MockPaymentProcessor.should_decline_payment(
                card.number, payment_request.amount
            )
            
            payment_method_response = PaymentMethodResponse(
                type=PaymentMethodType.CARD,
                card=CardDetails(
                    brand=card_brand,
                    last4=last4,
                    exp_month=card.exp_month,
                    exp_year=card.exp_year
                )
            )
            
            status = PaymentStatus.FAILED if should_decline else PaymentStatus.SUCCEEDED
            
        else:
            # For non-card payments, simulate high success rate
            import random
            should_decline = random.random() < 0.02  # 2% decline rate
            failure_code = "payment_failed" if should_decline else None
            failure_message = "Payment could not be processed." if should_decline else None
            
            payment_method_response = PaymentMethodResponse(
                type=payment_request.payment_method.type
            )
            
            status = PaymentStatus.FAILED if should_decline else PaymentStatus.SUCCEEDED
        
        return PaymentResponse(
            id=payment_id,
            amount=payment_request.amount,
            currency=payment_request.currency.lower(),
            status=status,
            payment_method=payment_method_response,
            customer_id=payment_request.customer_id,
            description=payment_request.description,
            statement_descriptor=payment_request.statement_descriptor,
            created=current_time,
            updated=current_time,
            transaction_id=transaction_id,
            receipt_url=f"https://api.portal.dev/receipts/{payment_id}",
            metadata=payment_request.metadata or {},
            failure_code=failure_code,
            failure_message=failure_message
        )

# In-memory storage for demo purposes (in production, use database)
MOCK_PAYMENTS: Dict[str, PaymentResponse] = {}

# API Endpoints

@router.post("/process", response_model=PaymentResponse)
async def process_payment(
    payment_request: PaymentRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.CREATE))
):
    """
    Process a payment immediately.
    
    This endpoint processes various payment methods including credit cards,
    bank accounts, and digital wallets. Returns immediate success or failure.
    """
    
    # Check for idempotency
    if payment_request.idempotency_key and payment_request.idempotency_key in MOCK_PAYMENTS:
        return MOCK_PAYMENTS[payment_request.idempotency_key]
    
    # Process the payment
    payment_response = MockPaymentProcessor.process_payment(payment_request)
    
    # Store in mock database
    MOCK_PAYMENTS[payment_response.id] = payment_response
    if payment_request.idempotency_key:
        MOCK_PAYMENTS[payment_request.idempotency_key] = payment_response
    
    return payment_response

@router.post("/authorize", response_model=PaymentResponse)
async def authorize_payment(
    authorize_request: AuthorizeRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.CREATE))
):
    """
    Authorize a payment without capturing funds.
    
    This reserves funds on the customer's payment method but doesn't capture them.
    Use the capture endpoint to complete the payment.
    """
    
    # Convert to payment request for processing
    payment_request = PaymentRequest(
        amount=authorize_request.amount,
        currency=authorize_request.currency,
        payment_method=authorize_request.payment_method,
        customer_id=authorize_request.customer_id,
        description=authorize_request.description,
        metadata=authorize_request.metadata
    )
    
    payment_response = MockPaymentProcessor.process_payment(payment_request)
    
    # Override status for authorization
    if payment_response.status == PaymentStatus.SUCCEEDED:
        payment_response.status = PaymentStatus.REQUIRES_ACTION
        payment_response.failure_code = None
        payment_response.failure_message = None
    
    MOCK_PAYMENTS[payment_response.id] = payment_response
    return payment_response

@router.post("/{payment_id}/capture", response_model=PaymentResponse)
async def capture_payment(
    payment_id: str,
    capture_request: CaptureRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.CREATE))
):
    """
    Capture a previously authorized payment.
    
    This completes the payment by capturing the authorized funds.
    Can capture partial amounts if specified.
    """
    
    if payment_id not in MOCK_PAYMENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment = MOCK_PAYMENTS[payment_id]
    
    if payment.status != PaymentStatus.REQUIRES_ACTION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment cannot be captured in its current state"
        )
    
    # Update payment status
    payment.status = PaymentStatus.SUCCEEDED
    payment.updated = int(time.time())
    
    # Handle partial capture
    if capture_request.amount and capture_request.amount < payment.amount:
        payment.amount = capture_request.amount
    
    if capture_request.statement_descriptor:
        payment.statement_descriptor = capture_request.statement_descriptor
    
    return payment

@router.post("/{payment_id}/void", response_model=PaymentResponse)
async def void_payment(
    payment_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.CREATE))
):
    """
    Void a previously authorized payment.
    
    This cancels the authorization and releases the held funds.
    Can only be done before capture.
    """
    
    if payment_id not in MOCK_PAYMENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    payment = MOCK_PAYMENTS[payment_id]
    
    if payment.status not in [PaymentStatus.REQUIRES_ACTION, PaymentStatus.PENDING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment cannot be voided in its current state"
        )
    
    payment.status = PaymentStatus.CANCELED
    payment.updated = int(time.time())
    
    return payment

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Retrieve a specific payment by ID.
    
    Returns complete payment details including status, amounts, and metadata.
    """
    
    if payment_id not in MOCK_PAYMENTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    return MOCK_PAYMENTS[payment_id]

@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    limit: int = Query(25, ge=1, le=100),
    starting_after: Optional[str] = Query(None),
    ending_before: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    status: Optional[PaymentStatus] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    List payments with optional filtering.
    
    Returns a paginated list of payments with support for filtering by
    customer, status, and other criteria.
    """
    
    # Filter payments
    payments = list(MOCK_PAYMENTS.values())
    
    if customer_id:
        payments = [p for p in payments if p.customer_id == customer_id]
    
    if status:
        payments = [p for p in payments if p.status == status]
    
    # Sort by creation time (newest first)
    payments.sort(key=lambda x: x.created, reverse=True)
    
    # Handle pagination
    start_index = 0
    if starting_after:
        try:
            start_index = next(i for i, p in enumerate(payments) if p.id == starting_after) + 1
        except StopIteration:
            start_index = 0
    
    if ending_before:
        try:
            end_index = next(i for i, p in enumerate(payments) if p.id == ending_before)
            payments = payments[:end_index]
        except StopIteration:
            pass
    
    # Apply limit
    paginated_payments = payments[start_index:start_index + limit]
    has_more = start_index + limit < len(payments)
    
    return PaymentListResponse(
        data=paginated_payments,
        has_more=has_more,
        total_count=len(payments),
        url="/marketplace/v1/payments"
    )

# Health check endpoint
@router.get("/health")
async def payment_api_health():
    """Health check for payment processing API."""
    return {
        "status": "healthy",
        "service": "payment_processing",
        "version": "1.0.0",
        "endpoints": [
            "POST /process",
            "POST /authorize", 
            "POST /{payment_id}/capture",
            "POST /{payment_id}/void",
            "GET /{payment_id}",
            "GET /"
        ],
        "mock_features": [
            "Multiple payment methods",
            "Realistic success/failure rates",
            "Card brand detection",
            "Fraud simulation",
            "Idempotency support"
        ]
    }