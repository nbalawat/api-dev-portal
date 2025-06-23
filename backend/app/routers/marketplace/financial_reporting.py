"""
Financial Reporting API - Comprehensive financial analytics and reporting.

This module provides advanced financial reporting capabilities including
revenue analytics, reconciliation reports, tax summaries, and custom reporting.
"""

import uuid
import time
import random
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

router = APIRouter(prefix="/v1/financial-reporting", tags=["Financial Reporting"])

# Financial Reporting Models

class ReportType(str, Enum):
    REVENUE_ANALYTICS = "revenue_analytics"
    RECONCILIATION = "reconciliation"
    TAX_SUMMARY = "tax_summary"
    CUSTOM_METRICS = "custom_metrics"
    CASH_FLOW = "cash_flow"
    PROFIT_LOSS = "profit_loss"

class ReportFormat(str, Enum):
    JSON = "json"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"

class ReportPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class ReportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RevenueCategory(str, Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    MARKETPLACE_FEES = "marketplace_fees"
    TRANSACTION_FEES = "transaction_fees"
    REFUNDS = "refunds"
    CHARGEBACKS = "chargebacks"

class CustomReportRequest(BaseModel):
    name: str
    description: Optional[str] = None
    report_type: ReportType
    format: ReportFormat = ReportFormat.JSON
    date_from: str = Field(..., description="Start date in YYYY-MM-DD format")
    date_to: str = Field(..., description="End date in YYYY-MM-DD format")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metrics: List[str] = Field(default_factory=list)
    group_by: Optional[List[str]] = Field(default_factory=list)
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class RevenueAnalyticsRequest(BaseModel):
    period: ReportPeriod = ReportPeriod.MONTHLY
    date_from: str
    date_to: str
    categories: Optional[List[RevenueCategory]] = None
    customer_segments: Optional[List[str]] = None
    include_forecasts: bool = False
    breakdown_by: Optional[List[str]] = Field(default_factory=list)

class ReconciliationRequest(BaseModel):
    period: ReportPeriod = ReportPeriod.DAILY
    date_from: str
    date_to: str
    account_types: Optional[List[str]] = None
    include_pending: bool = True
    auto_match: bool = True

class FinancialMetric(BaseModel):
    name: str
    value: float
    currency: str = "USD"
    change_percent: Optional[float] = None
    change_amount: Optional[float] = None
    period_comparison: Optional[str] = None

class RevenueBreakdown(BaseModel):
    category: RevenueCategory
    amount: float
    currency: str = "USD"
    transaction_count: int
    percentage_of_total: float
    period_over_period_change: float

class CashFlowEntry(BaseModel):
    date: str
    inflows: float
    outflows: float
    net_flow: float
    running_balance: float
    category: str
    description: str

class ReportResponse(BaseModel):
    id: str
    object: str = "financial_report"
    name: str
    report_type: ReportType
    format: ReportFormat
    status: ReportStatus
    created: int
    completed_at: Optional[int] = None
    expires_at: int
    download_url: Optional[str] = None
    summary: Dict[str, Any]
    metadata: Dict[str, str]

class RevenueAnalyticsResponse(BaseModel):
    id: str
    object: str = "revenue_analytics"
    period: ReportPeriod
    date_from: str
    date_to: str
    total_revenue: FinancialMetric
    revenue_breakdown: List[RevenueBreakdown]
    growth_metrics: Dict[str, FinancialMetric]
    top_customers: List[Dict[str, Any]]
    forecasts: Optional[Dict[str, Any]] = None
    created: int
    metadata: Dict[str, str]

class ReconciliationResponse(BaseModel):
    id: str
    object: str = "reconciliation_report"
    period: ReportPeriod
    date_from: str
    date_to: str
    total_transactions: int
    matched_transactions: int
    unmatched_transactions: int
    discrepancies: List[Dict[str, Any]]
    total_amount_matched: float
    total_amount_unmatched: float
    reconciliation_rate: float
    created: int
    metadata: Dict[str, str]

class TaxSummaryResponse(BaseModel):
    id: str
    object: str = "tax_summary"
    tax_year: int
    quarter: Optional[int] = None
    total_revenue: float
    total_fees: float
    net_income: float
    tax_categories: Dict[str, float]
    deductions: Dict[str, float]
    estimated_tax_liability: float
    payment_details: Dict[str, Any]
    created: int
    metadata: Dict[str, str]

# Mock Financial Data Generator

class MockFinancialReporting:
    
    @staticmethod
    def generate_revenue_analytics(request: RevenueAnalyticsRequest) -> RevenueAnalyticsResponse:
        """Generate comprehensive revenue analytics report."""
        
        report_id = f"rev_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Calculate date range
        date_from = datetime.strptime(request.date_from, "%Y-%m-%d")
        date_to = datetime.strptime(request.date_to, "%Y-%m-%d")
        days_diff = (date_to - date_from).days
        
        # Generate total revenue
        base_daily_revenue = random.uniform(5000, 50000)
        total_revenue_amount = base_daily_revenue * days_diff
        
        # Add seasonal variance
        for i in range(days_diff):
            current_date = date_from + timedelta(days=i)
            seasonal_factor = 1 + (0.2 * random.uniform(-1, 1))
            total_revenue_amount += base_daily_revenue * seasonal_factor
        
        total_revenue = FinancialMetric(
            name="Total Revenue",
            value=round(total_revenue_amount, 2),
            currency="USD",
            change_percent=round(random.uniform(-10, 25), 2),
            change_amount=round(total_revenue_amount * random.uniform(-0.1, 0.25), 2),
            period_comparison="previous_period"
        )
        
        # Generate revenue breakdown
        categories = request.categories or [cat for cat in RevenueCategory]
        revenue_breakdown = []
        
        remaining_amount = total_revenue_amount
        for i, category in enumerate(categories):
            if i == len(categories) - 1:
                # Last category gets remaining amount
                amount = remaining_amount
            else:
                # Generate percentage based on category type
                category_percentages = {
                    RevenueCategory.SUBSCRIPTION: 0.45,
                    RevenueCategory.ONE_TIME: 0.25,
                    RevenueCategory.MARKETPLACE_FEES: 0.15,
                    RevenueCategory.TRANSACTION_FEES: 0.10,
                    RevenueCategory.REFUNDS: -0.03,
                    RevenueCategory.CHARGEBACKS: -0.02
                }
                
                base_percentage = category_percentages.get(category, 0.1)
                variance = random.uniform(-0.05, 0.05)
                percentage = max(0, base_percentage + variance)
                amount = total_revenue_amount * percentage
                remaining_amount -= amount
            
            transaction_count = int(amount / random.uniform(25, 100))
            percentage_of_total = (amount / total_revenue_amount) * 100 if total_revenue_amount > 0 else 0
            
            revenue_breakdown.append(RevenueBreakdown(
                category=category,
                amount=round(amount, 2),
                currency="USD",
                transaction_count=transaction_count,
                percentage_of_total=round(percentage_of_total, 2),
                period_over_period_change=round(random.uniform(-15, 30), 2)
            ))
        
        # Generate growth metrics
        growth_metrics = {
            "monthly_recurring_revenue": FinancialMetric(
                name="Monthly Recurring Revenue",
                value=round(total_revenue_amount * 0.45, 2),
                currency="USD",
                change_percent=round(random.uniform(5, 25), 2)
            ),
            "average_revenue_per_user": FinancialMetric(
                name="Average Revenue Per User",
                value=round(random.uniform(25, 150), 2),
                currency="USD",
                change_percent=round(random.uniform(-5, 15), 2)
            ),
            "customer_lifetime_value": FinancialMetric(
                name="Customer Lifetime Value",
                value=round(random.uniform(200, 2000), 2),
                currency="USD",
                change_percent=round(random.uniform(0, 20), 2)
            )
        }
        
        # Generate top customers
        top_customers = []
        for i in range(10):
            customer_revenue = round(random.uniform(1000, 10000), 2)
            top_customers.append({
                "customer_id": f"cust_{uuid.uuid4().hex[:12]}",
                "customer_name": f"Customer {i+1}",
                "revenue": customer_revenue,
                "transaction_count": random.randint(5, 50),
                "first_transaction": (current_time - random.randint(86400, 86400*365)),
                "last_transaction": (current_time - random.randint(0, 86400*30))
            })
        
        top_customers.sort(key=lambda x: x["revenue"], reverse=True)
        
        # Generate forecasts if requested
        forecasts = None
        if request.include_forecasts:
            forecasts = {
                "next_month_revenue": {
                    "predicted_amount": round(total_revenue_amount * 1.1, 2),
                    "confidence": round(random.uniform(0.75, 0.95), 2),
                    "factors": ["seasonal_trends", "customer_growth", "market_conditions"]
                },
                "quarterly_projection": {
                    "predicted_amount": round(total_revenue_amount * 3.2, 2),
                    "confidence": round(random.uniform(0.70, 0.90), 2),
                    "growth_rate": round(random.uniform(10, 30), 2)
                }
            }
        
        return RevenueAnalyticsResponse(
            id=report_id,
            period=request.period,
            date_from=request.date_from,
            date_to=request.date_to,
            total_revenue=total_revenue,
            revenue_breakdown=revenue_breakdown,
            growth_metrics=growth_metrics,
            top_customers=top_customers,
            forecasts=forecasts,
            created=current_time,
            metadata={}
        )
    
    @staticmethod
    def generate_reconciliation_report(request: ReconciliationRequest) -> ReconciliationResponse:
        """Generate bank reconciliation report."""
        
        report_id = f"rec_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Generate transaction counts
        total_transactions = random.randint(500, 5000)
        match_rate = random.uniform(0.85, 0.98)
        matched_transactions = int(total_transactions * match_rate)
        unmatched_transactions = total_transactions - matched_transactions
        
        # Generate amounts
        total_amount = random.uniform(100000, 1000000)
        matched_amount = total_amount * match_rate
        unmatched_amount = total_amount - matched_amount
        
        # Generate discrepancies
        discrepancies = []
        for i in range(min(unmatched_transactions, 20)):  # Show up to 20 discrepancies
            discrepancy_amount = random.uniform(10, 1000)
            discrepancies.append({
                "transaction_id": f"txn_{uuid.uuid4().hex[:16]}",
                "date": (current_time - random.randint(0, 86400*7)),
                "amount": round(discrepancy_amount, 2),
                "description": f"Unmatched transaction #{i+1}",
                "type": random.choice(["missing_bank_record", "missing_internal_record", "amount_mismatch"]),
                "status": "pending_review"
            })
        
        return ReconciliationResponse(
            id=report_id,
            period=request.period,
            date_from=request.date_from,
            date_to=request.date_to,
            total_transactions=total_transactions,
            matched_transactions=matched_transactions,
            unmatched_transactions=unmatched_transactions,
            discrepancies=discrepancies,
            total_amount_matched=round(matched_amount, 2),
            total_amount_unmatched=round(unmatched_amount, 2),
            reconciliation_rate=round(match_rate * 100, 2),
            created=current_time,
            metadata={}
        )
    
    @staticmethod
    def generate_tax_summary(year: int, quarter: Optional[int] = None) -> TaxSummaryResponse:
        """Generate tax summary report."""
        
        report_id = f"tax_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Generate financial figures
        total_revenue = random.uniform(500000, 5000000)
        total_fees = total_revenue * random.uniform(0.15, 0.25)
        net_income = total_revenue - total_fees
        
        # Tax categories
        tax_categories = {
            "gross_receipts": round(total_revenue, 2),
            "service_revenue": round(total_revenue * 0.7, 2),
            "product_revenue": round(total_revenue * 0.3, 2),
            "interest_income": round(random.uniform(1000, 10000), 2),
            "other_income": round(random.uniform(500, 5000), 2)
        }
        
        # Deductions
        deductions = {
            "business_expenses": round(total_fees * 0.6, 2),
            "depreciation": round(random.uniform(5000, 50000), 2),
            "professional_services": round(random.uniform(10000, 100000), 2),
            "software_subscriptions": round(random.uniform(5000, 25000), 2),
            "office_expenses": round(random.uniform(2000, 15000), 2)
        }
        
        total_deductions = sum(deductions.values())
        taxable_income = max(0, net_income - total_deductions)
        estimated_tax_rate = random.uniform(0.21, 0.35)
        estimated_tax_liability = taxable_income * estimated_tax_rate
        
        # Payment details
        payment_details = {
            "estimated_payments_made": round(estimated_tax_liability * random.uniform(0.7, 0.9), 2),
            "balance_due": round(estimated_tax_liability * random.uniform(0.1, 0.3), 2),
            "next_payment_date": "2024-04-15",
            "payment_frequency": "quarterly" if quarter else "annual"
        }
        
        return TaxSummaryResponse(
            id=report_id,
            tax_year=year,
            quarter=quarter,
            total_revenue=round(total_revenue, 2),
            total_fees=round(total_fees, 2),
            net_income=round(net_income, 2),
            tax_categories=tax_categories,
            deductions=deductions,
            estimated_tax_liability=round(estimated_tax_liability, 2),
            payment_details=payment_details,
            created=current_time,
            metadata={}
        )
    
    @staticmethod
    def generate_cash_flow_report(date_from: str, date_to: str, period: ReportPeriod) -> Dict[str, Any]:
        """Generate cash flow statement."""
        
        date_start = datetime.strptime(date_from, "%Y-%m-%d")
        date_end = datetime.strptime(date_to, "%Y-%m-%d")
        
        # Determine period increment
        if period == ReportPeriod.DAILY:
            delta = timedelta(days=1)
        elif period == ReportPeriod.WEEKLY:
            delta = timedelta(weeks=1)
        elif period == ReportPeriod.MONTHLY:
            delta = timedelta(days=30)
        else:
            delta = timedelta(days=30)
        
        cash_flow_entries = []
        running_balance = random.uniform(50000, 200000)  # Starting balance
        
        current_date = date_start
        while current_date <= date_end:
            # Generate inflows and outflows
            inflows = random.uniform(5000, 25000)
            outflows = random.uniform(3000, 20000)
            net_flow = inflows - outflows
            running_balance += net_flow
            
            cash_flow_entries.append(CashFlowEntry(
                date=current_date.strftime("%Y-%m-%d"),
                inflows=round(inflows, 2),
                outflows=round(outflows, 2),
                net_flow=round(net_flow, 2),
                running_balance=round(running_balance, 2),
                category="operations",
                description=f"Operational cash flow for {current_date.strftime('%B %d, %Y')}"
            ))
            
            current_date += delta
        
        # Calculate summary metrics
        total_inflows = sum(entry.inflows for entry in cash_flow_entries)
        total_outflows = sum(entry.outflows for entry in cash_flow_entries)
        net_cash_flow = total_inflows - total_outflows
        
        return {
            "id": f"cf_{uuid.uuid4().hex[:24]}",
            "object": "cash_flow_report",
            "period": period.value,
            "date_from": date_from,
            "date_to": date_to,
            "entries": [entry.dict() for entry in cash_flow_entries],
            "summary": {
                "total_inflows": round(total_inflows, 2),
                "total_outflows": round(total_outflows, 2),
                "net_cash_flow": round(net_cash_flow, 2),
                "ending_balance": round(running_balance, 2),
                "average_daily_flow": round(net_cash_flow / len(cash_flow_entries), 2)
            },
            "created": int(time.time())
        }

# In-memory storage for demo purposes
MOCK_REPORTS: Dict[str, ReportResponse] = {}
MOCK_REVENUE_ANALYTICS: Dict[str, RevenueAnalyticsResponse] = {}
MOCK_RECONCILIATION_REPORTS: Dict[str, ReconciliationResponse] = {}
MOCK_TAX_SUMMARIES: Dict[str, TaxSummaryResponse] = {}

# API Endpoints

@router.post("/revenue-analytics", response_model=RevenueAnalyticsResponse)
async def generate_revenue_analytics(
    analytics_request: RevenueAnalyticsRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Generate comprehensive revenue analytics report.
    
    This endpoint provides detailed revenue analysis including breakdowns,
    growth metrics, top customers, and optional forecasting.
    """
    
    analytics_response = MockFinancialReporting.generate_revenue_analytics(analytics_request)
    
    # Store in mock database
    MOCK_REVENUE_ANALYTICS[analytics_response.id] = analytics_response
    
    return analytics_response

@router.post("/reconciliation", response_model=ReconciliationResponse)
async def generate_reconciliation_report(
    reconciliation_request: ReconciliationRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Generate bank reconciliation report.
    
    This endpoint creates reconciliation reports comparing internal transaction
    records with bank statements to identify discrepancies.
    """
    
    reconciliation_response = MockFinancialReporting.generate_reconciliation_report(reconciliation_request)
    
    # Store in mock database
    MOCK_RECONCILIATION_REPORTS[reconciliation_response.id] = reconciliation_response
    
    return reconciliation_response

@router.get("/tax-summary/{year}", response_model=TaxSummaryResponse)
async def get_tax_summary(
    year: int,
    quarter: Optional[int] = Query(None, ge=1, le=4, description="Quarter (1-4) for quarterly reports"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Generate tax summary report for a specific year or quarter.
    
    This endpoint provides comprehensive tax information including income,
    deductions, and estimated tax liability calculations.
    """
    
    tax_summary = MockFinancialReporting.generate_tax_summary(year, quarter)
    
    # Store in mock database
    MOCK_TAX_SUMMARIES[tax_summary.id] = tax_summary
    
    return tax_summary

@router.get("/cash-flow")
async def get_cash_flow_report(
    date_from: str = Query(..., description="Start date in YYYY-MM-DD format"),
    date_to: str = Query(..., description="End date in YYYY-MM-DD format"),
    period: ReportPeriod = Query(ReportPeriod.WEEKLY),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Generate cash flow statement.
    
    This endpoint provides detailed cash flow analysis showing inflows,
    outflows, and net cash position over time.
    """
    
    cash_flow_report = MockFinancialReporting.generate_cash_flow_report(date_from, date_to, period)
    return cash_flow_report

@router.post("/custom-report", response_model=ReportResponse)
async def create_custom_report(
    report_request: CustomReportRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.CREATE))
):
    """
    Create a custom financial report.
    
    This endpoint allows creation of customized reports with specific
    metrics, filters, and formatting options.
    """
    
    report_id = f"rpt_{uuid.uuid4().hex[:24]}"
    current_time = int(time.time())
    
    # Simulate report generation
    processing_time = random.randint(30, 300)  # 30 seconds to 5 minutes
    
    # Generate summary based on report type
    summary = {
        "metrics_count": len(report_request.metrics),
        "date_range": f"{report_request.date_from} to {report_request.date_to}",
        "filters_applied": len(report_request.filters),
        "estimated_size": f"{random.randint(100, 5000)} KB"
    }
    
    if report_request.report_type == ReportType.REVENUE_ANALYTICS:
        summary.update({
            "total_revenue": round(random.uniform(10000, 100000), 2),
            "transaction_count": random.randint(500, 5000)
        })
    elif report_request.report_type == ReportType.RECONCILIATION:
        summary.update({
            "reconciliation_rate": round(random.uniform(85, 98), 2),
            "discrepancies_found": random.randint(0, 50)
        })
    
    report_response = ReportResponse(
        id=report_id,
        name=report_request.name,
        report_type=report_request.report_type,
        format=report_request.format,
        status=ReportStatus.PROCESSING,
        created=current_time,
        expires_at=current_time + (7 * 24 * 60 * 60),  # 7 days
        download_url=f"https://api.example.com/reports/{report_id}/download",
        summary=summary,
        metadata=report_request.metadata or {}
    )
    
    # Store in mock database
    MOCK_REPORTS[report_id] = report_response
    
    return report_response

@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Retrieve a specific financial report by ID.
    
    Returns the current status and details of a report generation process.
    """
    
    if report_id not in MOCK_REPORTS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    report = MOCK_REPORTS[report_id]
    
    # Simulate report completion
    if report.status == ReportStatus.PROCESSING:
        current_time = int(time.time())
        if current_time - report.created > 60:  # Complete after 1 minute
            report.status = ReportStatus.COMPLETED
            report.completed_at = current_time
    
    return report

@router.get("/reports")
async def list_reports(
    limit: int = Query(25, ge=1, le=100),
    report_type: Optional[ReportType] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    List financial reports with optional filtering.
    
    Returns a paginated list of reports with support for filtering by
    type, status, and other criteria.
    """
    
    reports = list(MOCK_REPORTS.values())
    
    # Apply filters
    if report_type:
        reports = [r for r in reports if r.report_type == report_type]
    
    if status:
        reports = [r for r in reports if r.status == status]
    
    # Sort by creation time (newest first)
    reports.sort(key=lambda x: x.created, reverse=True)
    
    # Apply limit
    paginated_reports = reports[:limit]
    
    return {
        "object": "list",
        "data": paginated_reports,
        "has_more": len(reports) > limit,
        "total_count": len(reports),
        "url": "/marketplace/v1/financial-reporting/reports"
    }

@router.get("/analytics/summary")
async def get_reporting_analytics(
    days: int = Query(30, ge=1, le=365),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Get financial reporting analytics and statistics.
    
    Returns comprehensive metrics about report generation, popular report types,
    and financial data insights.
    """
    
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)
    
    # Filter reports within date range
    recent_reports = [r for r in MOCK_REPORTS.values() if r.created >= start_time]
    recent_revenue_reports = [r for r in MOCK_REVENUE_ANALYTICS.values() if r.created >= start_time]
    recent_reconciliation_reports = [r for r in MOCK_RECONCILIATION_REPORTS.values() if r.created >= start_time]
    
    # Report type breakdown
    report_type_breakdown = {}
    for report_type in ReportType:
        count = len([r for r in recent_reports if r.report_type == report_type])
        report_type_breakdown[report_type.value] = count
    
    # Status breakdown
    status_breakdown = {}
    for report_status in ReportStatus:
        count = len([r for r in recent_reports if r.status == report_status])
        status_breakdown[report_status.value] = count
    
    # Financial insights
    total_revenue_analyzed = sum(r.total_revenue.value for r in recent_revenue_reports)
    avg_reconciliation_rate = sum(r.reconciliation_rate for r in recent_reconciliation_reports) / max(len(recent_reconciliation_reports), 1)
    
    return {
        "period_days": days,
        "total_reports_generated": len(recent_reports),
        "report_type_breakdown": report_type_breakdown,
        "status_breakdown": status_breakdown,
        "completion_rate": round(status_breakdown.get("completed", 0) / max(len(recent_reports), 1) * 100, 2),
        "average_generation_time": "2.5 minutes",
        "financial_insights": {
            "total_revenue_analyzed": round(total_revenue_analyzed, 2),
            "average_reconciliation_rate": round(avg_reconciliation_rate, 2),
            "reports_with_discrepancies": len([r for r in recent_reconciliation_reports if r.unmatched_transactions > 0]),
            "top_revenue_categories": [
                {"category": "subscription", "percentage": 45},
                {"category": "one_time", "percentage": 25},
                {"category": "marketplace_fees", "percentage": 15}
            ]
        },
        "popular_report_formats": {
            "json": round(random.uniform(40, 60), 1),
            "pdf": round(random.uniform(20, 35), 1),
            "csv": round(random.uniform(15, 25), 1),
            "excel": round(random.uniform(5, 15), 1)
        }
    }

@router.get("/metrics/dashboard")
async def get_financial_dashboard_metrics(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.BILLING, Permission.READ))
):
    """
    Get key financial metrics for dashboard display.
    
    Returns essential financial KPIs and metrics for real-time monitoring
    and dashboard display purposes.
    """
    
    current_time = int(time.time())
    
    # Generate current period metrics
    metrics = {
        "revenue": {
            "current_month": round(random.uniform(50000, 200000), 2),
            "previous_month": round(random.uniform(45000, 180000), 2),
            "month_over_month_change": round(random.uniform(-5, 25), 2),
            "ytd_total": round(random.uniform(500000, 2000000), 2)
        },
        "cash_flow": {
            "current_balance": round(random.uniform(100000, 500000), 2),
            "weekly_net_flow": round(random.uniform(-10000, 50000), 2),
            "burn_rate": round(random.uniform(10000, 75000), 2),
            "runway_months": round(random.uniform(6, 24), 1)
        },
        "reconciliation": {
            "pending_reconciliation": random.randint(0, 25),
            "last_reconciliation_date": current_time - random.randint(86400, 86400*7),
            "reconciliation_accuracy": round(random.uniform(92, 99), 2),
            "unresolved_discrepancies": random.randint(0, 10)
        },
        "tax_compliance": {
            "next_filing_due": current_time + random.randint(86400*7, 86400*90),
            "estimated_quarterly_liability": round(random.uniform(10000, 100000), 2),
            "ytd_payments_made": round(random.uniform(50000, 300000), 2),
            "compliance_status": "on_track"
        },
        "key_ratios": {
            "gross_margin": round(random.uniform(65, 85), 2),
            "operating_margin": round(random.uniform(15, 35), 2),
            "quick_ratio": round(random.uniform(1.2, 3.5), 2),
            "debt_to_equity": round(random.uniform(0.1, 0.8), 2)
        }
    }
    
    return {
        "timestamp": current_time,
        "metrics": metrics,
        "alerts": [
            {
                "type": "info",
                "message": "Monthly financial reports are ready for review",
                "priority": "medium"
            },
            {
                "type": "warning", 
                "message": f"{metrics['reconciliation']['pending_reconciliation']} transactions need reconciliation",
                "priority": "high" if metrics['reconciliation']['pending_reconciliation'] > 10 else "low"
            }
        ],
        "last_updated": current_time
    }

# Health check endpoint
@router.get("/health")
async def financial_reporting_api_health():
    """Health check for financial reporting API."""
    return {
        "status": "healthy",
        "service": "financial_reporting",
        "version": "1.0.0",
        "endpoints": [
            "POST /revenue-analytics",
            "POST /reconciliation",
            "GET /tax-summary/{year}",
            "GET /cash-flow",
            "POST /custom-report",
            "GET /reports/{report_id}",
            "GET /reports",
            "GET /analytics/summary",
            "GET /metrics/dashboard"
        ],
        "mock_features": [
            "Revenue analytics with forecasting",
            "Bank reconciliation automation", 
            "Tax summary generation",
            "Cash flow analysis",
            "Custom report builder",
            "Financial dashboard metrics"
        ],
        "supported_formats": len(ReportFormat),
        "report_types": len(ReportType),
        "supported_periods": len(ReportPeriod)
    }