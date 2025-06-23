"""
Bank Account Verification API - ACH verification and account validation.

This module provides comprehensive bank account verification including micro-deposits,
instant verification, and ACH network validation for secure payment processing.
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

router = APIRouter(prefix="/v1/bank-verification", tags=["Bank Account Verification"])

# Bank Verification Models

class VerificationMethod(str, Enum):
    MICRO_DEPOSITS = "micro_deposits"
    INSTANT = "instant"
    PLAID_LINK = "plaid_link"
    MANUAL = "manual"

class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFICATION_REQUIRED = "verification_required"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class BankAccountType(str, Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    BUSINESS_CHECKING = "business_checking"
    BUSINESS_SAVINGS = "business_savings"

class BankVerificationRequest(BaseModel):
    account_number: str = Field(..., min_length=4, max_length=17)
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_holder_name: str
    account_type: BankAccountType = BankAccountType.CHECKING
    customer_id: str
    verification_method: VerificationMethod = VerificationMethod.MICRO_DEPOSITS
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class MicroDepositConfirmation(BaseModel):
    amount1: float = Field(..., ge=0.01, le=0.99, description="First micro-deposit amount in dollars")
    amount2: float = Field(..., ge=0.01, le=0.99, description="Second micro-deposit amount in dollars")

class InstantVerificationRequest(BaseModel):
    account_number: str = Field(..., min_length=4, max_length=17)
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_holder_name: str
    account_type: BankAccountType = BankAccountType.CHECKING
    customer_id: str
    ssn_last4: Optional[str] = Field(None, min_length=4, max_length=4, description="Last 4 digits of SSN")
    phone: Optional[str] = None
    email: Optional[str] = None

class BankInfo(BaseModel):
    name: str
    routing_number: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None

class VerificationResponse(BaseModel):
    id: str
    object: str = "bank_verification"
    status: VerificationStatus
    method: VerificationMethod
    account_holder_name: str
    account_type: BankAccountType
    bank_info: BankInfo
    last4: str
    customer_id: str
    created: int
    updated: int
    verified_at: Optional[int] = None
    expires_at: Optional[int] = None
    attempts_remaining: int
    micro_deposits: Optional[Dict[str, Any]] = None
    metadata: Dict[str, str]

class VerificationListResponse(BaseModel):
    object: str = "list"
    data: List[VerificationResponse]
    has_more: bool
    total_count: int
    url: str

# Mock Bank Database
MOCK_BANKS = {
    "021000021": {
        "name": "Chase Bank",
        "address": "1 Chase Manhattan Plaza",
        "city": "New York",
        "state": "NY",
        "zip_code": "10005",
        "phone": "1-800-935-9935",
        "website": "chase.com"
    },
    "111000025": {
        "name": "Wells Fargo Bank",
        "address": "420 Montgomery Street",
        "city": "San Francisco", 
        "state": "CA",
        "zip_code": "94163",
        "phone": "1-800-869-3557",
        "website": "wellsfargo.com"
    },
    "121000248": {
        "name": "Bank of America",
        "address": "100 North Tryon Street",
        "city": "Charlotte",
        "state": "NC", 
        "zip_code": "28255",
        "phone": "1-800-432-1000",
        "website": "bankofamerica.com"
    },
    "011401533": {
        "name": "PNC Bank",
        "address": "The Tower at PNC Plaza",
        "city": "Pittsburgh",
        "state": "PA",
        "zip_code": "15222",
        "phone": "1-888-762-2265",
        "website": "pnc.com"
    },
    "054001204": {
        "name": "Citibank",
        "address": "388 Greenwich Street",
        "city": "New York",
        "state": "NY",
        "zip_code": "10013",
        "phone": "1-800-374-9700",
        "website": "citibank.com"
    }
}

# Mock Bank Account Verification Logic

class MockBankVerificationProcessor:
    
    @staticmethod
    def validate_routing_number(routing_number: str) -> bool:
        """Validate routing number using checksum algorithm."""
        if len(routing_number) != 9 or not routing_number.isdigit():
            return False
        
        # ABA routing number checksum validation
        digits = [int(d) for d in routing_number]
        checksum = (
            3 * (digits[0] + digits[3] + digits[6]) +
            7 * (digits[1] + digits[4] + digits[7]) +
            1 * (digits[2] + digits[5] + digits[8])
        )
        return checksum % 10 == 0
    
    @staticmethod
    def get_bank_info(routing_number: str) -> BankInfo:
        """Get bank information from routing number."""
        bank_data = MOCK_BANKS.get(routing_number)
        if not bank_data:
            # Return generic bank info for unknown routing numbers
            return BankInfo(
                name="Unknown Bank",
                routing_number=routing_number,
                address="Unknown",
                city="Unknown",
                state="Unknown"
            )
        
        return BankInfo(
            name=bank_data["name"],
            routing_number=routing_number,
            address=bank_data.get("address"),
            city=bank_data.get("city"),
            state=bank_data.get("state"),
            zip_code=bank_data.get("zip_code"),
            phone=bank_data.get("phone"),
            website=bank_data.get("website")
        )
    
    @staticmethod
    def should_fail_verification(routing_number: str, account_number: str, method: VerificationMethod) -> tuple[bool, Optional[str]]:
        """Determine if verification should fail based on test scenarios."""
        
        # Test routing numbers that always fail
        fail_routing_numbers = ["999999999", "000000000", "123456789"]
        if routing_number in fail_routing_numbers:
            return True, "invalid_routing_number"
        
        # Test account numbers that fail
        if account_number == "000000000":
            return True, "invalid_account_number"
        
        # Method-specific failures
        if method == VerificationMethod.INSTANT:
            # Higher failure rate for instant verification
            import random
            if random.random() < 0.15:  # 15% failure rate
                return True, "verification_failed"
        
        # Random failure for realistic behavior (5% failure rate)
        import random
        if random.random() < 0.05:
            return True, "verification_failed"
        
        return False, None
    
    @staticmethod
    def generate_micro_deposits() -> tuple[float, float]:
        """Generate two random micro-deposit amounts."""
        import random
        amount1 = round(random.uniform(0.01, 0.99), 2)
        amount2 = round(random.uniform(0.01, 0.99), 2)
        return amount1, amount2
    
    @staticmethod
    def process_verification(request: BankVerificationRequest) -> VerificationResponse:
        """Process a bank account verification request."""
        
        verification_id = f"bav_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Validate routing number
        if not MockBankVerificationProcessor.validate_routing_number(request.routing_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid routing number format or checksum"
            )
        
        # Get bank information
        bank_info = MockBankVerificationProcessor.get_bank_info(request.routing_number)
        
        # Check if verification should fail
        should_fail, failure_reason = MockBankVerificationProcessor.should_fail_verification(
            request.routing_number, request.account_number, request.verification_method
        )
        
        # Determine verification status and method-specific data
        if should_fail:
            verification_status = VerificationStatus.FAILED
            verified_at = None
            expires_at = None
            attempts_remaining = 0
            micro_deposits = None
        elif request.verification_method == VerificationMethod.INSTANT:
            verification_status = VerificationStatus.VERIFIED
            verified_at = current_time
            expires_at = None
            attempts_remaining = 0
            micro_deposits = None
        else:  # MICRO_DEPOSITS
            verification_status = VerificationStatus.VERIFICATION_REQUIRED
            verified_at = None
            expires_at = current_time + (7 * 24 * 60 * 60)  # 7 days to verify
            attempts_remaining = 3
            
            # Generate micro deposits
            amount1, amount2 = MockBankVerificationProcessor.generate_micro_deposits()
            micro_deposits = {
                "amount1": amount1,
                "amount2": amount2,
                "sent_at": current_time,
                "attempts_used": 0
            }
        
        return VerificationResponse(
            id=verification_id,
            status=verification_status,
            method=request.verification_method,
            account_holder_name=request.account_holder_name,
            account_type=request.account_type,
            bank_info=bank_info,
            last4=request.account_number[-4:],
            customer_id=request.customer_id,
            created=current_time,
            updated=current_time,
            verified_at=verified_at,
            expires_at=expires_at,
            attempts_remaining=attempts_remaining,
            micro_deposits=micro_deposits,
            metadata=request.metadata or {}
        )

# In-memory storage for demo purposes
MOCK_VERIFICATIONS: Dict[str, VerificationResponse] = {}

# API Endpoints

@router.post("/initiate", response_model=VerificationResponse)
async def initiate_verification(
    verification_request: BankVerificationRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.CREATE))
):
    """
    Initiate bank account verification.
    
    This endpoint starts the verification process for a bank account using
    either micro-deposits or instant verification methods.
    """
    
    verification_response = MockBankVerificationProcessor.process_verification(verification_request)
    
    # Store in mock database
    MOCK_VERIFICATIONS[verification_response.id] = verification_response
    
    return verification_response

@router.post("/instant", response_model=VerificationResponse)
async def instant_verification(
    instant_request: InstantVerificationRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.CREATE))
):
    """
    Perform instant bank account verification.
    
    This endpoint attempts immediate verification using bank network APIs
    and customer information validation.
    """
    
    # Convert to standard verification request
    verification_request = BankVerificationRequest(
        account_number=instant_request.account_number,
        routing_number=instant_request.routing_number,
        account_holder_name=instant_request.account_holder_name,
        account_type=instant_request.account_type,
        customer_id=instant_request.customer_id,
        verification_method=VerificationMethod.INSTANT,
        metadata={
            "ssn_last4_provided": bool(instant_request.ssn_last4),
            "phone_provided": bool(instant_request.phone),
            "email_provided": bool(instant_request.email)
        }
    )
    
    verification_response = MockBankVerificationProcessor.process_verification(verification_request)
    
    # Store in mock database
    MOCK_VERIFICATIONS[verification_response.id] = verification_response
    
    return verification_response

@router.post("/{verification_id}/confirm", response_model=VerificationResponse)
async def confirm_micro_deposits(
    verification_id: str,
    confirmation: MicroDepositConfirmation,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.UPDATE))
):
    """
    Confirm micro-deposit amounts to complete verification.
    
    This endpoint allows customers to confirm the micro-deposit amounts
    they received in their bank account.
    """
    
    if verification_id not in MOCK_VERIFICATIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found"
        )
    
    verification = MOCK_VERIFICATIONS[verification_id]
    
    if verification.status != VerificationStatus.VERIFICATION_REQUIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification is not in a state that accepts confirmation"
        )
    
    if verification.attempts_remaining <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification attempts remaining"
        )
    
    # Check if verification has expired
    current_time = int(time.time())
    if verification.expires_at and current_time > verification.expires_at:
        verification.status = VerificationStatus.EXPIRED
        verification.updated = current_time
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification has expired"
        )
    
    # Validate micro-deposit amounts
    if verification.micro_deposits:
        expected_amount1 = verification.micro_deposits["amount1"]
        expected_amount2 = verification.micro_deposits["amount2"]
        
        if (abs(confirmation.amount1 - expected_amount1) < 0.01 and
            abs(confirmation.amount2 - expected_amount2) < 0.01):
            # Verification successful
            verification.status = VerificationStatus.VERIFIED
            verification.verified_at = current_time
            verification.attempts_remaining = 0
        else:
            # Verification failed
            verification.attempts_remaining -= 1
            verification.micro_deposits["attempts_used"] += 1
            
            if verification.attempts_remaining <= 0:
                verification.status = VerificationStatus.FAILED
    
    verification.updated = current_time
    
    return verification

@router.get("/{verification_id}", response_model=VerificationResponse)
async def get_verification(
    verification_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    Retrieve a bank account verification by ID.
    
    Returns the current status and details of a verification process.
    """
    
    if verification_id not in MOCK_VERIFICATIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification not found"
        )
    
    return MOCK_VERIFICATIONS[verification_id]

@router.get("/", response_model=VerificationListResponse)
async def list_verifications(
    limit: int = Query(25, ge=1, le=100),
    customer_id: Optional[str] = Query(None),
    status: Optional[VerificationStatus] = Query(None),
    method: Optional[VerificationMethod] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    List bank account verifications with optional filtering.
    
    Returns a paginated list of verifications with support for filtering by
    customer, status, verification method, and other criteria.
    """
    
    # Filter verifications
    verifications = list(MOCK_VERIFICATIONS.values())
    
    if customer_id:
        verifications = [v for v in verifications if v.customer_id == customer_id]
    
    if status:
        verifications = [v for v in verifications if v.status == status]
    
    if method:
        verifications = [v for v in verifications if v.method == method]
    
    # Sort by creation time (newest first)
    verifications.sort(key=lambda x: x.created, reverse=True)
    
    # Apply limit
    paginated_verifications = verifications[:limit]
    has_more = len(verifications) > limit
    
    return VerificationListResponse(
        data=paginated_verifications,
        has_more=has_more,
        total_count=len(verifications),
        url="/marketplace/v1/bank-verification"
    )

@router.get("/routing/{routing_number}/info")
async def get_bank_info(
    routing_number: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    Get bank information from routing number.
    
    Returns detailed information about the bank associated with
    the provided routing number.
    """
    
    if not MockBankVerificationProcessor.validate_routing_number(routing_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid routing number format"
        )
    
    bank_info = MockBankVerificationProcessor.get_bank_info(routing_number)
    
    return {
        "routing_number": routing_number,
        "bank": bank_info.dict(),
        "valid": routing_number in MOCK_BANKS,
        "supports_ach": True,
        "supports_wire": True
    }

@router.get("/analytics/summary")
async def get_verification_analytics(
    days: int = Query(30, ge=1, le=365),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT_METHOD, Permission.READ))
):
    """
    Get bank verification analytics and statistics.
    
    Returns comprehensive metrics about verification success rates,
    methods used, and processing times.
    """
    
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)
    
    # Filter verifications within date range
    recent_verifications = [v for v in MOCK_VERIFICATIONS.values() if v.created >= start_time]
    
    # Calculate metrics
    total_verifications = len(recent_verifications)
    
    # Status breakdown
    status_breakdown = {}
    for verification_status in VerificationStatus:
        status_count = len([v for v in recent_verifications if v.status == verification_status])
        status_breakdown[verification_status.value] = status_count
    
    # Method breakdown
    method_breakdown = {}
    for verification_method in VerificationMethod:
        method_count = len([v for v in recent_verifications if v.method == verification_method])
        method_breakdown[verification_method.value] = method_count
    
    # Success rate calculation
    verified_count = status_breakdown.get("verified", 0)
    success_rate = (verified_count / total_verifications * 100) if total_verifications > 0 else 0
    
    # Average verification time (for completed verifications)
    completed_verifications = [v for v in recent_verifications if v.verified_at]
    avg_verification_time = 0
    if completed_verifications:
        total_time = sum(v.verified_at - v.created for v in completed_verifications)
        avg_verification_time = total_time / len(completed_verifications)
    
    # Bank distribution
    bank_breakdown = {}
    for verification in recent_verifications:
        bank_name = verification.bank_info.name
        bank_breakdown[bank_name] = bank_breakdown.get(bank_name, 0) + 1
    
    return {
        "period_days": days,
        "total_verifications": total_verifications,
        "success_rate_percent": round(success_rate, 2),
        "average_verification_time_seconds": round(avg_verification_time, 2),
        "status_breakdown": status_breakdown,
        "method_breakdown": method_breakdown,
        "top_banks": dict(sorted(bank_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]),
        "instant_verification_rate": round(method_breakdown.get("instant", 0) / total_verifications * 100, 2) if total_verifications > 0 else 0,
        "micro_deposit_success_rate": round(
            len([v for v in recent_verifications if v.method == VerificationMethod.MICRO_DEPOSITS and v.status == VerificationStatus.VERIFIED]) /
            max(method_breakdown.get("micro_deposits", 1), 1) * 100, 2
        )
    }

# Health check endpoint
@router.get("/health")
async def bank_verification_api_health():
    """Health check for bank account verification API."""
    return {
        "status": "healthy",
        "service": "bank_account_verification",
        "version": "1.0.0",
        "endpoints": [
            "POST /initiate",
            "POST /instant",
            "POST /{verification_id}/confirm",
            "GET /{verification_id}",
            "GET /",
            "GET /routing/{routing_number}/info",
            "GET /analytics/summary"
        ],
        "mock_features": [
            "Micro-deposit verification",
            "Instant verification",
            "ACH routing number validation",
            "Bank information lookup",
            "Verification analytics"
        ],
        "supported_banks": len(MOCK_BANKS),
        "test_routing_numbers": list(MOCK_BANKS.keys())
    }