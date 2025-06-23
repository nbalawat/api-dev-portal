"""
Transaction History API - Comprehensive transaction tracking and reporting.

This module provides advanced transaction querying, filtering, and analytics
with support for detailed reporting and data export capabilities.
"""

import uuid
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
import json

from ...dependencies.database import get_database
from ...middleware import require_api_key
from ...middleware.permissions import require_resource_permission
from ...core.permissions import ResourceType, Permission
from ...models.api_key import APIKey
from .payments import MOCK_PAYMENTS, PaymentStatus
from .refunds import MOCK_REFUNDS, RefundStatus

router = APIRouter(prefix="/v1/transactions", tags=["Transaction History"])

# Transaction Models

class TransactionType(str, Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    PAYOUT = "payout"
    ADJUSTMENT = "adjustment"
    FEE = "fee"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"

class Transaction(BaseModel):
    id: str
    type: TransactionType
    status: TransactionStatus
    amount: float
    currency: str
    fee: float = 0.0
    net_amount: float
    customer_id: Optional[str] = None
    payment_method_type: Optional[str] = None
    description: Optional[str] = None
    created: int
    updated: int
    reference_id: str  # ID of the underlying payment/refund/etc
    metadata: Dict[str, str] = Field(default_factory=dict)

class TransactionAnalytics(BaseModel):
    total_transactions: int
    total_amount: float
    total_fees: float
    net_amount: float
    success_rate: float
    average_transaction_size: float
    transaction_count_by_type: Dict[str, int]
    transaction_amount_by_type: Dict[str, float]
    transaction_count_by_status: Dict[str, int]
    top_customers: List[Dict[str, Union[str, float, int]]]
    daily_volume: List[Dict[str, Union[str, float, int]]]

class TransactionSearchRequest(BaseModel):
    query: str
    customer_id: Optional[str] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    transaction_type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None

class TransactionListResponse(BaseModel):
    object: str = "list"
    data: List[Transaction]
    has_more: bool
    total_count: int
    url: str

# Mock Transaction Processing

class MockTransactionProcessor:
    
    @staticmethod
    def calculate_fees(amount: float, transaction_type: TransactionType) -> float:
        """Calculate processing fees based on transaction type and amount."""
        
        fee_rates = {
            TransactionType.PAYMENT: 0.029,  # 2.9%
            TransactionType.REFUND: 0.0,     # No fee for refunds
            TransactionType.PAYOUT: 0.025,   # 2.5%
            TransactionType.ADJUSTMENT: 0.0,  # No fee for adjustments
            TransactionType.FEE: 0.0         # No fee on fees
        }
        
        base_fee = amount * fee_rates.get(transaction_type, 0.0)
        
        # Add fixed fee for payments
        if transaction_type == TransactionType.PAYMENT:
            base_fee += 0.30  # $0.30 fixed fee
        
        return round(base_fee, 2)
    
    @staticmethod
    def create_transaction_from_payment(payment_id: str, payment_data: Any) -> Transaction:
        """Create a transaction record from a payment."""
        
        fee = MockTransactionProcessor.calculate_fees(payment_data.amount, TransactionType.PAYMENT)
        net_amount = payment_data.amount - fee
        
        return Transaction(
            id=f"txn_{uuid.uuid4().hex[:24]}",
            type=TransactionType.PAYMENT,
            status=TransactionStatus.SUCCEEDED if payment_data.status == PaymentStatus.SUCCEEDED else TransactionStatus.FAILED,
            amount=payment_data.amount,
            currency=payment_data.currency,
            fee=fee,
            net_amount=net_amount,
            customer_id=payment_data.customer_id,
            payment_method_type=payment_data.payment_method.type.value if payment_data.payment_method else None,
            description=payment_data.description,
            created=payment_data.created,
            updated=payment_data.updated,
            reference_id=payment_id,
            metadata=payment_data.metadata or {}
        )
    
    @staticmethod
    def create_transaction_from_refund(refund_id: str, refund_data: Any) -> Transaction:
        """Create a transaction record from a refund."""
        
        fee = MockTransactionProcessor.calculate_fees(refund_data.amount, TransactionType.REFUND)
        net_amount = -refund_data.amount - fee  # Negative because it's money going out
        
        return Transaction(
            id=f"txn_{uuid.uuid4().hex[:24]}",
            type=TransactionType.REFUND,
            status=TransactionStatus.SUCCEEDED if refund_data.status == RefundStatus.SUCCEEDED else TransactionStatus.FAILED,
            amount=-refund_data.amount,  # Negative for refunds
            currency=refund_data.currency,
            fee=fee,
            net_amount=net_amount,
            customer_id=None,  # Would need to look up from original payment
            payment_method_type=None,
            description=f"Refund for payment {refund_data.payment_id}",
            created=refund_data.created,
            updated=refund_data.updated,
            reference_id=refund_id,
            metadata=refund_data.metadata or {}
        )
    
    @staticmethod
    def get_all_transactions() -> List[Transaction]:
        """Generate transaction list from all payments and refunds."""
        
        transactions = []
        
        # Create transactions from payments
        for payment_id, payment in MOCK_PAYMENTS.items():
            if payment_id.startswith('pay_'):  # Only process actual payment IDs
                transaction = MockTransactionProcessor.create_transaction_from_payment(payment_id, payment)
                transactions.append(transaction)
        
        # Create transactions from refunds
        for refund_id, refund in MOCK_REFUNDS.items():
            transaction = MockTransactionProcessor.create_transaction_from_refund(refund_id, refund)
            transactions.append(transaction)
        
        return transactions

# API Endpoints

@router.get("/list", response_model=TransactionListResponse)
async def list_transactions(
    limit: int = Query(25, ge=1, le=100),
    starting_after: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    status: Optional[TransactionStatus] = Query(None),
    date_from: Optional[str] = Query(None, description="ISO date string (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="ISO date string (YYYY-MM-DD)"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.TRANSACTION, Permission.READ))
):
    """
    List transactions with comprehensive filtering options.
    
    Returns a paginated list of transactions with support for filtering by
    customer, type, status, date range, and other criteria.
    """
    
    # Get all transactions
    transactions = MockTransactionProcessor.get_all_transactions()
    
    # Apply filters
    if customer_id:
        transactions = [t for t in transactions if t.customer_id == customer_id]
    
    if transaction_type:
        transactions = [t for t in transactions if t.type == transaction_type]
    
    if status:
        transactions = [t for t in transactions if t.status == status]
    
    # Date filtering
    if date_from:
        date_from_ts = int(datetime.fromisoformat(date_from).timestamp())
        transactions = [t for t in transactions if t.created >= date_from_ts]
    
    if date_to:
        date_to_ts = int(datetime.fromisoformat(date_to).timestamp())
        transactions = [t for t in transactions if t.created <= date_to_ts]
    
    # Sort by creation time (newest first)
    transactions.sort(key=lambda x: x.created, reverse=True)
    
    # Handle pagination
    start_index = 0
    if starting_after:
        try:
            start_index = next(i for i, t in enumerate(transactions) if t.id == starting_after) + 1
        except StopIteration:
            start_index = 0
    
    # Apply limit
    paginated_transactions = transactions[start_index:start_index + limit]
    has_more = start_index + limit < len(transactions)
    
    return TransactionListResponse(
        data=paginated_transactions,
        has_more=has_more,
        total_count=len(transactions),
        url="/marketplace/v1/transactions/list"
    )

@router.get("/{transaction_id}", response_model=Transaction)
async def get_transaction(
    transaction_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.TRANSACTION, Permission.READ))
):
    """
    Retrieve a specific transaction by ID.
    
    Returns complete transaction details including fees, net amounts, and metadata.
    """
    
    transactions = MockTransactionProcessor.get_all_transactions()
    
    for transaction in transactions:
        if transaction.id == transaction_id:
            return transaction
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Transaction not found"
    )

@router.post("/search", response_model=TransactionListResponse)
async def search_transactions(
    search_request: TransactionSearchRequest,
    limit: int = Query(25, ge=1, le=100),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.TRANSACTION, Permission.READ))
):
    """
    Advanced transaction search with text queries and filters.
    
    Supports searching across transaction descriptions, customer IDs,
    and reference IDs with additional filtering options.
    """
    
    transactions = MockTransactionProcessor.get_all_transactions()
    
    # Text search
    if search_request.query:
        query_lower = search_request.query.lower()
        transactions = [
            t for t in transactions
            if (t.description and query_lower in t.description.lower()) or
               (t.customer_id and query_lower in t.customer_id.lower()) or
               query_lower in t.reference_id.lower() or
               query_lower in t.id.lower()
        ]
    
    # Apply additional filters
    if search_request.customer_id:
        transactions = [t for t in transactions if t.customer_id == search_request.customer_id]
    
    if search_request.transaction_type:
        transactions = [t for t in transactions if t.type == search_request.transaction_type]
    
    if search_request.status:
        transactions = [t for t in transactions if t.status == search_request.status]
    
    # Amount range filtering
    if search_request.amount_min is not None:
        transactions = [t for t in transactions if abs(t.amount) >= search_request.amount_min]
    
    if search_request.amount_max is not None:
        transactions = [t for t in transactions if abs(t.amount) <= search_request.amount_max]
    
    # Date filtering
    if search_request.date_from:
        date_from_ts = int(datetime.fromisoformat(search_request.date_from).timestamp())
        transactions = [t for t in transactions if t.created >= date_from_ts]
    
    if search_request.date_to:
        date_to_ts = int(datetime.fromisoformat(search_request.date_to).timestamp())
        transactions = [t for t in transactions if t.created <= date_to_ts]
    
    # Sort and paginate
    transactions.sort(key=lambda x: x.created, reverse=True)
    paginated_transactions = transactions[:limit]
    
    return TransactionListResponse(
        data=paginated_transactions,
        has_more=len(transactions) > limit,
        total_count=len(transactions),
        url="/marketplace/v1/transactions/search"
    )

@router.get("/analytics/summary", response_model=TransactionAnalytics)
async def get_transaction_analytics(
    days: int = Query(30, ge=1, le=365),
    customer_id: Optional[str] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.TRANSACTION, Permission.READ))
):
    """
    Get comprehensive transaction analytics and insights.
    
    Returns detailed statistics including volume, success rates, top customers,
    and trends over the specified time period.
    """
    
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)
    
    # Get transactions within date range
    transactions = MockTransactionProcessor.get_all_transactions()
    filtered_transactions = [t for t in transactions if t.created >= start_time]
    
    if customer_id:
        filtered_transactions = [t for t in filtered_transactions if t.customer_id == customer_id]
    
    # Calculate basic metrics
    total_transactions = len(filtered_transactions)
    total_amount = sum(abs(t.amount) for t in filtered_transactions)
    total_fees = sum(t.fee for t in filtered_transactions)
    net_amount = sum(t.net_amount for t in filtered_transactions)
    
    successful_transactions = [t for t in filtered_transactions if t.status == TransactionStatus.SUCCEEDED]
    success_rate = (len(successful_transactions) / total_transactions * 100) if total_transactions > 0 else 0
    
    average_transaction_size = total_amount / total_transactions if total_transactions > 0 else 0
    
    # Transaction count by type
    transaction_count_by_type = {}
    transaction_amount_by_type = {}
    for transaction_type in TransactionType:
        type_transactions = [t for t in filtered_transactions if t.type == transaction_type]
        transaction_count_by_type[transaction_type.value] = len(type_transactions)
        transaction_amount_by_type[transaction_type.value] = sum(abs(t.amount) for t in type_transactions)
    
    # Transaction count by status
    transaction_count_by_status = {}
    for transaction_status in TransactionStatus:
        status_transactions = [t for t in filtered_transactions if t.status == transaction_status]
        transaction_count_by_status[transaction_status.value] = len(status_transactions)
    
    # Top customers (by transaction volume)
    customer_volumes = {}
    for t in filtered_transactions:
        if t.customer_id:
            if t.customer_id not in customer_volumes:
                customer_volumes[t.customer_id] = {"amount": 0, "count": 0}
            customer_volumes[t.customer_id]["amount"] += abs(t.amount)
            customer_volumes[t.customer_id]["count"] += 1
    
    top_customers = [
        {
            "customer_id": customer_id,
            "total_amount": data["amount"],
            "transaction_count": data["count"]
        }
        for customer_id, data in sorted(customer_volumes.items(), key=lambda x: x[1]["amount"], reverse=True)[:10]
    ]
    
    # Daily volume (last 30 days or specified period)
    daily_volumes = {}
    period_days = min(days, 30)  # Limit to 30 days for performance
    
    for i in range(period_days):
        day_start = current_time - ((i + 1) * 24 * 60 * 60)
        day_end = current_time - (i * 24 * 60 * 60)
        
        day_transactions = [t for t in filtered_transactions if day_start <= t.created < day_end]
        daily_volumes[datetime.fromtimestamp(day_start).strftime('%Y-%m-%d')] = {
            "date": datetime.fromtimestamp(day_start).strftime('%Y-%m-%d'),
            "transaction_count": len(day_transactions),
            "total_amount": sum(abs(t.amount) for t in day_transactions)
        }
    
    daily_volume = list(daily_volumes.values())
    daily_volume.sort(key=lambda x: x["date"])
    
    return TransactionAnalytics(
        total_transactions=total_transactions,
        total_amount=round(total_amount, 2),
        total_fees=round(total_fees, 2),
        net_amount=round(net_amount, 2),
        success_rate=round(success_rate, 2),
        average_transaction_size=round(average_transaction_size, 2),
        transaction_count_by_type=transaction_count_by_type,
        transaction_amount_by_type={k: round(v, 2) for k, v in transaction_amount_by_type.items()},
        transaction_count_by_status=transaction_count_by_status,
        top_customers=top_customers,
        daily_volume=daily_volume
    )

@router.get("/export/{format}")
async def export_transactions(
    format: ExportFormat,
    customer_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.TRANSACTION, Permission.READ))
):
    """
    Export transaction data in various formats.
    
    Supports JSON, CSV, and Excel export formats with the same filtering
    options as the list endpoint.
    """
    
    # Get filtered transactions
    transactions = MockTransactionProcessor.get_all_transactions()
    
    # Apply filters (same logic as list endpoint)
    if customer_id:
        transactions = [t for t in transactions if t.customer_id == customer_id]
    
    if transaction_type:
        transactions = [t for t in transactions if t.type == transaction_type]
    
    if date_from:
        date_from_ts = int(datetime.fromisoformat(date_from).timestamp())
        transactions = [t for t in transactions if t.created >= date_from_ts]
    
    if date_to:
        date_to_ts = int(datetime.fromisoformat(date_to).timestamp())
        transactions = [t for t in transactions if t.created <= date_to_ts]
    
    # Sort by creation time
    transactions.sort(key=lambda x: x.created, reverse=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transactions_export_{timestamp}.{format.value}"
    
    if format == ExportFormat.JSON:
        # JSON export
        export_data = [t.dict() for t in transactions]
        json_str = json.dumps(export_data, indent=2, default=str)
        
        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    elif format == ExportFormat.CSV:
        # CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        if transactions:
            headers = list(transactions[0].dict().keys())
            writer.writerow(headers)
            
            # Write data
            for transaction in transactions:
                row = [str(value) for value in transaction.dict().values()]
                writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    else:  # XLSX format
        # For demo purposes, return CSV with Excel mime type
        # In production, use openpyxl or similar library
        output = io.StringIO()
        writer = csv.writer(output)
        
        if transactions:
            headers = list(transactions[0].dict().keys())
            writer.writerow(headers)
            
            for transaction in transactions:
                row = [str(value) for value in transaction.dict().values()]
                writer.writerow(row)
        
        csv_content = output.getvalue()
        output.close()
        
        return Response(
            content=csv_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

# Health check endpoint
@router.get("/health")
async def transaction_api_health():
    """Health check for transaction history API."""
    return {
        "status": "healthy",
        "service": "transaction_history",
        "version": "1.0.0",
        "endpoints": [
            "GET /list",
            "GET /{transaction_id}",
            "POST /search",
            "GET /analytics/summary",
            "GET /export/{format}"
        ],
        "mock_features": [
            "Comprehensive transaction tracking",
            "Advanced filtering and search",
            "Analytics and reporting",
            "Data export (JSON, CSV, Excel)",
            "Fee calculation and net amounts"
        ]
    }