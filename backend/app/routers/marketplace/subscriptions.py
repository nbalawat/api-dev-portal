"""
Subscription Billing API - Recurring payment management for the mock payment ecosystem.

This module provides comprehensive subscription management including billing cycles,
plan management, prorations, and subscription lifecycle operations.
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

router = APIRouter(prefix="/v1/subscriptions", tags=["Subscription Billing"])

# Subscription Models

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    PAUSED = "paused"

class BillingInterval(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"

class ProrationBehavior(str, Enum):
    CREATE_PRORATIONS = "create_prorations"
    NONE = "none"
    ALWAYS_INVOICE = "always_invoice"

class CancelationReason(str, Enum):
    USER_REQUESTED = "user_requested"
    PAYMENT_FAILED = "payment_failed"
    FRAUD = "fraud"
    BUSINESS_DECISION = "business_decision"
    OTHER = "other"

class BillingPlan(BaseModel):
    id: str
    name: str
    amount: float
    currency: str = "USD"
    interval: BillingInterval
    interval_count: int = 1
    trial_period_days: Optional[int] = None
    active: bool = True
    metadata: Dict[str, str] = Field(default_factory=dict)

class SubscriptionItem(BaseModel):
    plan_id: str
    quantity: int = 1
    metadata: Dict[str, str] = Field(default_factory=dict)

class SubscriptionRequest(BaseModel):
    customer_id: str
    plan_id: str
    payment_method_id: str
    trial_period_days: Optional[int] = None
    billing_cycle_anchor: Optional[str] = None
    proration_behavior: ProrationBehavior = ProrationBehavior.CREATE_PRORATIONS
    collection_method: str = Field(default="charge_automatically")
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class UpdateSubscriptionRequest(BaseModel):
    plan_id: Optional[str] = None
    quantity: Optional[int] = None
    proration_behavior: ProrationBehavior = ProrationBehavior.CREATE_PRORATIONS
    trial_end: Optional[str] = None
    pause_collection: Optional[bool] = None
    metadata: Optional[Dict[str, str]] = None

class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True
    reason: CancelationReason = CancelationReason.USER_REQUESTED
    feedback: Optional[str] = None

class Invoice(BaseModel):
    id: str
    subscription_id: str
    amount_due: float
    amount_paid: float
    currency: str
    status: str
    period_start: int
    period_end: int
    created: int
    due_date: int
    paid: bool
    attempt_count: int

class SubscriptionResponse(BaseModel):
    id: str
    object: str = "subscription"
    customer_id: str
    plan: BillingPlan
    status: SubscriptionStatus
    current_period_start: int
    current_period_end: int
    trial_start: Optional[int] = None
    trial_end: Optional[int] = None
    canceled_at: Optional[int] = None
    cancel_at_period_end: bool = False
    cancel_at: Optional[int] = None
    created: int
    updated: int
    quantity: int = 1
    metadata: Dict[str, str]
    latest_invoice: Optional[Invoice] = None

class SubscriptionListResponse(BaseModel):
    object: str = "list"
    data: List[SubscriptionResponse]
    has_more: bool
    total_count: int
    url: str

# Mock Plans Database
MOCK_PLANS: Dict[str, BillingPlan] = {
    "plan_basic_monthly": BillingPlan(
        id="plan_basic_monthly",
        name="Basic Monthly",
        amount=9.99,
        currency="USD",
        interval=BillingInterval.MONTH,
        interval_count=1,
        trial_period_days=7
    ),
    "plan_premium_monthly": BillingPlan(
        id="plan_premium_monthly",
        name="Premium Monthly",
        amount=29.99,
        currency="USD",
        interval=BillingInterval.MONTH,
        interval_count=1,
        trial_period_days=14
    ),
    "plan_enterprise_monthly": BillingPlan(
        id="plan_enterprise_monthly",
        name="Enterprise Monthly",
        amount=99.99,
        currency="USD",
        interval=BillingInterval.MONTH,
        interval_count=1
    ),
    "plan_basic_yearly": BillingPlan(
        id="plan_basic_yearly",
        name="Basic Yearly",
        amount=99.99,
        currency="USD",
        interval=BillingInterval.YEAR,
        interval_count=1,
        trial_period_days=30
    ),
    "plan_premium_yearly": BillingPlan(
        id="plan_premium_yearly",
        name="Premium Yearly",
        amount=299.99,
        currency="USD",
        interval=BillingInterval.YEAR,
        interval_count=1,
        trial_period_days=30
    )
}

# Mock Subscription Processing Logic

class MockSubscriptionProcessor:
    
    @staticmethod
    def calculate_period_dates(interval: BillingInterval, interval_count: int, anchor: Optional[datetime] = None) -> tuple[int, int]:
        """Calculate subscription period start and end dates."""
        start_date = anchor or datetime.utcnow()
        
        if interval == BillingInterval.DAY:
            end_date = start_date + timedelta(days=interval_count)
        elif interval == BillingInterval.WEEK:
            end_date = start_date + timedelta(weeks=interval_count)
        elif interval == BillingInterval.MONTH:
            # Handle month calculation more carefully
            if start_date.month + interval_count <= 12:
                end_date = start_date.replace(month=start_date.month + interval_count)
            else:
                years_to_add = (start_date.month + interval_count - 1) // 12
                new_month = (start_date.month + interval_count - 1) % 12 + 1
                end_date = start_date.replace(year=start_date.year + years_to_add, month=new_month)
        elif interval == BillingInterval.YEAR:
            end_date = start_date.replace(year=start_date.year + interval_count)
        
        return int(start_date.timestamp()), int(end_date.timestamp())
    
    @staticmethod
    def should_fail_subscription(plan_id: str, customer_id: str) -> tuple[bool, Optional[str]]:
        """Determine if subscription creation should fail."""
        
        # Random failure for realistic behavior (3% failure rate)
        import random
        if random.random() < 0.03:
            return True, "payment_method_declined"
        
        # Simulate customer credit issues for high-value plans
        if "enterprise" in plan_id and random.random() < 0.1:
            return True, "insufficient_funds"
        
        return False, None
    
    @staticmethod
    def create_invoice(subscription: SubscriptionResponse) -> Invoice:
        """Create an invoice for a subscription."""
        invoice_id = f"in_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        return Invoice(
            id=invoice_id,
            subscription_id=subscription.id,
            amount_due=subscription.plan.amount,
            amount_paid=subscription.plan.amount if subscription.status == SubscriptionStatus.ACTIVE else 0,
            currency=subscription.plan.currency.lower(),
            status="paid" if subscription.status == SubscriptionStatus.ACTIVE else "open",
            period_start=subscription.current_period_start,
            period_end=subscription.current_period_end,
            created=current_time,
            due_date=subscription.current_period_end,
            paid=subscription.status == SubscriptionStatus.ACTIVE,
            attempt_count=1
        )
    
    @staticmethod
    def process_subscription(subscription_request: SubscriptionRequest) -> SubscriptionResponse:
        """Process a subscription creation request."""
        
        subscription_id = f"sub_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Get the plan
        if subscription_request.plan_id not in MOCK_PLANS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        
        plan = MOCK_PLANS[subscription_request.plan_id]
        
        # Check if subscription should fail
        should_fail, failure_reason = MockSubscriptionProcessor.should_fail_subscription(
            subscription_request.plan_id, subscription_request.customer_id
        )
        
        # Calculate trial period
        trial_start = None
        trial_end = None
        trial_days = subscription_request.trial_period_days or plan.trial_period_days
        
        if trial_days and trial_days > 0:
            trial_start = current_time
            trial_end = current_time + (trial_days * 24 * 60 * 60)
            status = SubscriptionStatus.TRIALING
        elif should_fail:
            status = SubscriptionStatus.INCOMPLETE
        else:
            status = SubscriptionStatus.ACTIVE
        
        # Calculate billing period
        anchor_date = None
        if subscription_request.billing_cycle_anchor:
            anchor_date = datetime.fromisoformat(subscription_request.billing_cycle_anchor.replace('Z', '+00:00'))
        
        period_start, period_end = MockSubscriptionProcessor.calculate_period_dates(
            plan.interval, plan.interval_count, anchor_date
        )
        
        subscription = SubscriptionResponse(
            id=subscription_id,
            customer_id=subscription_request.customer_id,
            plan=plan,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_start=trial_start,
            trial_end=trial_end,
            created=current_time,
            updated=current_time,
            metadata=subscription_request.metadata or {}
        )
        
        # Create initial invoice if not in trial
        if status == SubscriptionStatus.ACTIVE:
            subscription.latest_invoice = MockSubscriptionProcessor.create_invoice(subscription)
        
        return subscription

# In-memory storage for demo purposes
MOCK_SUBSCRIPTIONS: Dict[str, SubscriptionResponse] = {}

# API Endpoints

@router.post("/create", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_request: SubscriptionRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.CREATE))
):
    """
    Create a new subscription.
    
    This endpoint creates a recurring subscription for a customer with the specified plan.
    Supports trial periods, custom billing cycles, and various payment options.
    """
    
    subscription_response = MockSubscriptionProcessor.process_subscription(subscription_request)
    
    # Store in mock database
    MOCK_SUBSCRIPTIONS[subscription_response.id] = subscription_response
    
    return subscription_response

@router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.READ))
):
    """
    Retrieve a specific subscription by ID.
    
    Returns complete subscription details including current status, billing information,
    and trial period details.
    """
    
    if subscription_id not in MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    return MOCK_SUBSCRIPTIONS[subscription_id]

@router.post("/{subscription_id}/update", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: str,
    update_request: UpdateSubscriptionRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.CREATE))
):
    """
    Update an existing subscription.
    
    This endpoint allows changing plans, quantities, and other subscription settings
    with proper proration handling.
    """
    
    if subscription_id not in MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    subscription = MOCK_SUBSCRIPTIONS[subscription_id]
    
    # Update plan if specified
    if update_request.plan_id:
        if update_request.plan_id not in MOCK_PLANS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found"
            )
        subscription.plan = MOCK_PLANS[update_request.plan_id]
    
    # Update quantity
    if update_request.quantity is not None:
        subscription.quantity = update_request.quantity
    
    # Handle pause/unpause
    if update_request.pause_collection is not None:
        if update_request.pause_collection:
            subscription.status = SubscriptionStatus.PAUSED
        elif subscription.status == SubscriptionStatus.PAUSED:
            subscription.status = SubscriptionStatus.ACTIVE
    
    # Update metadata
    if update_request.metadata is not None:
        subscription.metadata.update(update_request.metadata)
    
    subscription.updated = int(time.time())
    
    return subscription

@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: str,
    cancel_request: CancelSubscriptionRequest = CancelSubscriptionRequest(),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.CREATE))
):
    """
    Cancel a subscription.
    
    This endpoint cancels a subscription either immediately or at the end of the
    current billing period based on the cancel_at_period_end parameter.
    """
    
    if subscription_id not in MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    subscription = MOCK_SUBSCRIPTIONS[subscription_id]
    
    if subscription.status in [SubscriptionStatus.CANCELED, SubscriptionStatus.INCOMPLETE_EXPIRED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription is already canceled"
        )
    
    current_time = int(time.time())
    
    if cancel_request.cancel_at_period_end:
        subscription.cancel_at_period_end = True
        subscription.cancel_at = subscription.current_period_end
    else:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = current_time
    
    subscription.updated = current_time
    
    return subscription

@router.get("/{subscription_id}/invoices", response_model=List[Invoice])
async def get_subscription_invoices(
    subscription_id: str,
    limit: int = Query(25, ge=1, le=100),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.READ))
):
    """
    Get invoices for a subscription.
    
    Returns a list of all invoices generated for the specified subscription.
    """
    
    if subscription_id not in MOCK_SUBSCRIPTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    subscription = MOCK_SUBSCRIPTIONS[subscription_id]
    
    # Generate mock historical invoices
    invoices = []
    if subscription.latest_invoice:
        invoices.append(subscription.latest_invoice)
    
    # Add some historical invoices for demonstration
    current_time = int(time.time())
    for i in range(1, min(6, limit)):  # Generate up to 5 historical invoices
        invoice_date = current_time - (i * 30 * 24 * 60 * 60)  # Monthly intervals
        historical_invoice = Invoice(
            id=f"in_historical_{i}_{uuid.uuid4().hex[:16]}",
            subscription_id=subscription_id,
            amount_due=subscription.plan.amount,
            amount_paid=subscription.plan.amount,
            currency=subscription.plan.currency.lower(),
            status="paid",
            period_start=invoice_date - (30 * 24 * 60 * 60),
            period_end=invoice_date,
            created=invoice_date,
            due_date=invoice_date,
            paid=True,
            attempt_count=1
        )
        invoices.append(historical_invoice)
    
    return invoices[:limit]

@router.get("/", response_model=SubscriptionListResponse)
async def list_subscriptions(
    limit: int = Query(25, ge=1, le=100),
    starting_after: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    status: Optional[SubscriptionStatus] = Query(None),
    plan_id: Optional[str] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.READ))
):
    """
    List subscriptions with optional filtering.
    
    Returns a paginated list of subscriptions with support for filtering by
    customer, status, plan, and other criteria.
    """
    
    # Filter subscriptions
    subscriptions = list(MOCK_SUBSCRIPTIONS.values())
    
    if customer_id:
        subscriptions = [s for s in subscriptions if s.customer_id == customer_id]
    
    if status:
        subscriptions = [s for s in subscriptions if s.status == status]
    
    if plan_id:
        subscriptions = [s for s in subscriptions if s.plan.id == plan_id]
    
    # Sort by creation time (newest first)
    subscriptions.sort(key=lambda x: x.created, reverse=True)
    
    # Handle pagination
    start_index = 0
    if starting_after:
        try:
            start_index = next(i for i, s in enumerate(subscriptions) if s.id == starting_after) + 1
        except StopIteration:
            start_index = 0
    
    # Apply limit
    paginated_subscriptions = subscriptions[start_index:start_index + limit]
    has_more = start_index + limit < len(subscriptions)
    
    return SubscriptionListResponse(
        data=paginated_subscriptions,
        has_more=has_more,
        total_count=len(subscriptions),
        url="/marketplace/v1/subscriptions"
    )

@router.get("/plans/list", response_model=List[BillingPlan])
async def list_plans(
    active_only: bool = Query(True),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.SUBSCRIPTION, Permission.READ))
):
    """
    List available billing plans.
    
    Returns all available subscription plans with pricing and interval information.
    """
    
    plans = list(MOCK_PLANS.values())
    
    if active_only:
        plans = [p for p in plans if p.active]
    
    return plans

# Health check endpoint
@router.get("/health")
async def subscription_api_health():
    """Health check for subscription billing API."""
    return {
        "status": "healthy",
        "service": "subscription_billing",
        "version": "1.0.0",
        "endpoints": [
            "POST /create",
            "GET /{subscription_id}",
            "POST /{subscription_id}/update",
            "POST /{subscription_id}/cancel",
            "GET /{subscription_id}/invoices",
            "GET /",
            "GET /plans/list"
        ],
        "mock_features": [
            "Flexible billing intervals",
            "Trial period support",
            "Plan changes with proration",
            "Invoice generation",
            "Subscription lifecycle management"
        ],
        "available_plans": len(MOCK_PLANS)
    }