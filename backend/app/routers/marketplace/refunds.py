"""
Refund Management API - Handle payment refunds for the mock payment ecosystem.

This module provides comprehensive refund management with support for full/partial
refunds, refund tracking, and realistic processing scenarios.
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
from .payments import MOCK_PAYMENTS, PaymentStatus

router = APIRouter(prefix="/v1/refunds", tags=["Refund Management"])

# Refund Models

class RefundStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

class RefundReason(str, Enum):
    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"
    EXPIRED_UNCAPTURED_CHARGE = "expired_uncaptured_charge"
    PRODUCT_UNACCEPTABLE = "product_unacceptable"
    SERVICE_NOT_PROVIDED = "service_not_provided"
    OTHER = "other"

class RefundRequest(BaseModel):
    payment_id: str
    amount: Optional[float] = Field(None, gt=0, le=999999.99)
    reason: RefundReason = RefundReason.REQUESTED_BY_CUSTOMER
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)
    refund_application_fee: bool = Field(default=False)
    reverse_transfer: bool = Field(default=False)

class RefundResponse(BaseModel):
    id: str
    object: str = "refund"
    amount: float
    currency: str
    status: RefundStatus
    payment_id: str
    reason: RefundReason
    created: int
    updated: int
    metadata: Dict[str, str]
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None
    receipt_number: Optional[str] = None

class RefundListResponse(BaseModel):
    object: str = "list"
    data: List[RefundResponse]
    has_more: bool
    total_count: int
    url: str

# Mock Refund Processing Logic

class MockRefundProcessor:
    
    @staticmethod
    def should_fail_refund(amount: float, payment_id: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Determine if refund should fail based on test scenarios."""
        
        # Random failure for realistic behavior (2% failure rate)
        import random
        if random.random() < 0.02:
            return True, "refund_failed", "Refund could not be processed."
        
        # Simulate bank rejection for very old payments
        if payment_id.endswith("old"):
            return True, "charge_already_refunded", "This payment has already been fully refunded."
        
        return False, None, None
    
    @staticmethod
    def process_refund(refund_request: RefundRequest) -> RefundResponse:
        """Process a refund request and return the result."""
        
        refund_id = f"re_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Get the original payment
        if refund_request.payment_id not in MOCK_PAYMENTS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        payment = MOCK_PAYMENTS[refund_request.payment_id]
        
        # Validate payment status
        if payment.status != PaymentStatus.SUCCEEDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot refund payment that is not succeeded"
            )
        
        # Determine refund amount
        refund_amount = refund_request.amount if refund_request.amount else payment.amount
        
        if refund_amount > payment.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund amount cannot exceed payment amount"
            )
        
        # Check if refund should fail
        should_fail, failure_code, failure_message = MockRefundProcessor.should_fail_refund(
            refund_amount, refund_request.payment_id
        )
        
        status_value = RefundStatus.FAILED if should_fail else RefundStatus.SUCCEEDED
        receipt_number = f"RN{uuid.uuid4().hex[:12].upper()}" if not should_fail else None
        
        return RefundResponse(
            id=refund_id,
            amount=refund_amount,
            currency=payment.currency,
            status=status_value,
            payment_id=refund_request.payment_id,
            reason=refund_request.reason,
            created=current_time,
            updated=current_time,
            metadata=refund_request.metadata or {},
            failure_code=failure_code,
            failure_message=failure_message,
            receipt_number=receipt_number
        )

# In-memory storage for demo purposes
MOCK_REFUNDS: Dict[str, RefundResponse] = {}

# API Endpoints

@router.post("/create", response_model=RefundResponse)
async def create_refund(
    refund_request: RefundRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.REFUND, Permission.CREATE))
):
    """
    Create a refund for a payment.
    
    This endpoint creates a full or partial refund for a previously successful payment.
    Supports various refund reasons and metadata for tracking.
    """
    
    refund_response = MockRefundProcessor.process_refund(refund_request)
    
    # Store in mock database
    MOCK_REFUNDS[refund_response.id] = refund_response
    
    return refund_response

@router.get("/{refund_id}", response_model=RefundResponse)
async def get_refund(
    refund_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.REFUND, Permission.READ))
):
    """
    Retrieve a specific refund by ID.
    
    Returns complete refund details including status, amounts, and metadata.
    """
    
    if refund_id not in MOCK_REFUNDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    return MOCK_REFUNDS[refund_id]

@router.get("/", response_model=RefundListResponse)
async def list_refunds(
    limit: int = Query(25, ge=1, le=100),
    starting_after: Optional[str] = Query(None),
    ending_before: Optional[str] = Query(None),
    payment_id: Optional[str] = Query(None),
    status: Optional[RefundStatus] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.REFUND, Permission.READ))
):
    """
    List refunds with optional filtering.
    
    Returns a paginated list of refunds with support for filtering by
    payment, status, and other criteria.
    """
    
    # Filter refunds
    refunds = list(MOCK_REFUNDS.values())
    
    if payment_id:
        refunds = [r for r in refunds if r.payment_id == payment_id]
    
    if status:
        refunds = [r for r in refunds if r.status == status]
    
    # Sort by creation time (newest first)
    refunds.sort(key=lambda x: x.created, reverse=True)
    
    # Handle pagination
    start_index = 0
    if starting_after:
        try:
            start_index = next(i for i, r in enumerate(refunds) if r.id == starting_after) + 1
        except StopIteration:
            start_index = 0
    
    if ending_before:
        try:
            end_index = next(i for i, r in enumerate(refunds) if r.id == ending_before)
            refunds = refunds[:end_index]
        except StopIteration:
            pass
    
    # Apply limit
    paginated_refunds = refunds[start_index:start_index + limit]
    has_more = start_index + limit < len(refunds)
    
    return RefundListResponse(
        data=paginated_refunds,
        has_more=has_more,
        total_count=len(refunds),
        url="/marketplace/v1/refunds"
    )

@router.post("/{refund_id}/cancel", response_model=RefundResponse)
async def cancel_refund(
    refund_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.REFUND, Permission.CREATE))
):
    """
    Cancel a pending refund.
    
    This cancels a refund that is still in pending status.
    Cannot cancel refunds that are already processed.
    """
    
    if refund_id not in MOCK_REFUNDS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )
    
    refund = MOCK_REFUNDS[refund_id]
    
    if refund.status != RefundStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only cancel pending refunds"
        )
    
    refund.status = RefundStatus.CANCELED
    refund.updated = int(time.time())
    
    return refund

@router.get("/analytics/summary")
async def get_refund_analytics(
    days: int = Query(30, ge=1, le=365),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.REFUND, Permission.READ))
):
    """
    Get refund analytics and summary statistics.
    
    Returns comprehensive refund metrics including rates, amounts, and trends.
    """
    
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)
    
    # Filter refunds within date range
    recent_refunds = [r for r in MOCK_REFUNDS.values() if r.created >= start_time]
    recent_payments = [p for p in MOCK_PAYMENTS.values() if p.created >= start_time]
    
    # Calculate metrics
    total_refunds = len(recent_refunds)
    total_payments = len(recent_payments)
    refund_rate = (total_refunds / total_payments * 100) if total_payments > 0 else 0
    
    total_refund_amount = sum(r.amount for r in recent_refunds if r.status == RefundStatus.SUCCEEDED)
    total_payment_amount = sum(p.amount for p in recent_payments if p.status == PaymentStatus.SUCCEEDED)
    
    refund_amount_rate = (total_refund_amount / total_payment_amount * 100) if total_payment_amount > 0 else 0
    
    # Refund reasons breakdown
    reason_breakdown = {}
    for refund in recent_refunds:
        reason_breakdown[refund.reason.value] = reason_breakdown.get(refund.reason.value, 0) + 1
    
    # Status breakdown
    status_breakdown = {}
    for refund in recent_refunds:
        status_breakdown[refund.status.value] = status_breakdown.get(refund.status.value, 0) + 1
    
    # Average refund amount
    successful_refunds = [r for r in recent_refunds if r.status == RefundStatus.SUCCEEDED]
    avg_refund_amount = sum(r.amount for r in successful_refunds) / len(successful_refunds) if successful_refunds else 0
    
    return {
        "period_days": days,
        "total_refunds": total_refunds,
        "total_payments": total_payments,
        "refund_rate_percent": round(refund_rate, 2),
        "total_refund_amount": round(total_refund_amount, 2),
        "total_payment_amount": round(total_payment_amount, 2),
        "refund_amount_rate_percent": round(refund_amount_rate, 2),
        "average_refund_amount": round(avg_refund_amount, 2),
        "reason_breakdown": reason_breakdown,
        "status_breakdown": status_breakdown,
        "trends": {
            "note": "In a real implementation, this would include daily/weekly trends",
            "sample_data": True
        }
    }

# Health check endpoint
@router.get("/health")
async def refund_api_health():
    """Health check for refund management API."""
    return {
        "status": "healthy",
        "service": "refund_management",
        "version": "1.0.0",
        "endpoints": [
            "POST /create",
            "GET /{refund_id}",
            "GET /",
            "POST /{refund_id}/cancel",
            "GET /analytics/summary"
        ],
        "mock_features": [
            "Full and partial refunds",
            "Multiple refund reasons",
            "Realistic success/failure rates",
            "Analytics and reporting",
            "Refund cancellation"
        ]
    }