"""
Currency Exchange API - Real-time currency conversion and exchange rates.

This module provides comprehensive currency exchange functionality including
real-time rates, historical data, currency conversion, and multi-currency support.
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

router = APIRouter(prefix="/v1/fx", tags=["Currency Exchange"])

# Currency Exchange Models

class SupportedCurrency(str, Enum):
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    JPY = "JPY"  # Japanese Yen
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    CHF = "CHF"  # Swiss Franc
    CNY = "CNY"  # Chinese Yuan
    SEK = "SEK"  # Swedish Krona
    NZD = "NZD"  # New Zealand Dollar
    MXN = "MXN"  # Mexican Peso
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar
    NOK = "NOK"  # Norwegian Krone
    KRW = "KRW"  # South Korean Won
    TRY = "TRY"  # Turkish Lira
    RUB = "RUB"  # Russian Ruble
    INR = "INR"  # Indian Rupee
    BRL = "BRL"  # Brazilian Real
    ZAR = "ZAR"  # South African Rand

class ExchangeRateProvider(str, Enum):
    MARKET = "market"
    CENTRAL_BANK = "central_bank"
    COMMERCIAL = "commercial"
    CRYPTOCURRENCY = "cryptocurrency"

class ConversionRequest(BaseModel):
    from_currency: SupportedCurrency
    to_currency: SupportedCurrency
    amount: float = Field(..., gt=0, le=1000000)
    rate_type: ExchangeRateProvider = ExchangeRateProvider.MARKET
    customer_id: Optional[str] = None
    reference: Optional[str] = None
    metadata: Optional[Dict[str, str]] = Field(default_factory=dict)

class ExchangeRate(BaseModel):
    from_currency: SupportedCurrency
    to_currency: SupportedCurrency
    rate: float
    inverse_rate: float
    bid: float
    ask: float
    mid: float
    spread_percent: float
    provider: ExchangeRateProvider
    timestamp: int
    source: str
    expires_at: int

class CurrencyInfo(BaseModel):
    code: SupportedCurrency
    name: str
    symbol: str
    decimal_places: int
    country: str
    is_crypto: bool = False

class ConversionResult(BaseModel):
    id: str
    from_currency: SupportedCurrency
    to_currency: SupportedCurrency
    from_amount: float
    to_amount: float
    exchange_rate: float
    rate_used: ExchangeRate
    fees: float
    net_amount: float
    customer_id: Optional[str]
    reference: Optional[str]
    created: int
    expires_at: int
    status: str
    metadata: Dict[str, str]

class RateHistoryEntry(BaseModel):
    timestamp: int
    rate: float
    volume: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None

class RateHistoryResponse(BaseModel):
    from_currency: SupportedCurrency
    to_currency: SupportedCurrency
    period: str
    data: List[RateHistoryEntry]
    total_entries: int

# Mock Currency Data

CURRENCY_INFO = {
    SupportedCurrency.USD: CurrencyInfo(code=SupportedCurrency.USD, name="US Dollar", symbol="$", decimal_places=2, country="United States"),
    SupportedCurrency.EUR: CurrencyInfo(code=SupportedCurrency.EUR, name="Euro", symbol="€", decimal_places=2, country="European Union"),
    SupportedCurrency.GBP: CurrencyInfo(code=SupportedCurrency.GBP, name="British Pound Sterling", symbol="£", decimal_places=2, country="United Kingdom"),
    SupportedCurrency.JPY: CurrencyInfo(code=SupportedCurrency.JPY, name="Japanese Yen", symbol="¥", decimal_places=0, country="Japan"),
    SupportedCurrency.CAD: CurrencyInfo(code=SupportedCurrency.CAD, name="Canadian Dollar", symbol="C$", decimal_places=2, country="Canada"),
    SupportedCurrency.AUD: CurrencyInfo(code=SupportedCurrency.AUD, name="Australian Dollar", symbol="A$", decimal_places=2, country="Australia"),
    SupportedCurrency.CHF: CurrencyInfo(code=SupportedCurrency.CHF, name="Swiss Franc", symbol="CHF", decimal_places=2, country="Switzerland"),
    SupportedCurrency.CNY: CurrencyInfo(code=SupportedCurrency.CNY, name="Chinese Yuan", symbol="¥", decimal_places=2, country="China"),
    SupportedCurrency.SEK: CurrencyInfo(code=SupportedCurrency.SEK, name="Swedish Krona", symbol="kr", decimal_places=2, country="Sweden"),
    SupportedCurrency.NZD: CurrencyInfo(code=SupportedCurrency.NZD, name="New Zealand Dollar", symbol="NZ$", decimal_places=2, country="New Zealand"),
    SupportedCurrency.MXN: CurrencyInfo(code=SupportedCurrency.MXN, name="Mexican Peso", symbol="$", decimal_places=2, country="Mexico"),
    SupportedCurrency.SGD: CurrencyInfo(code=SupportedCurrency.SGD, name="Singapore Dollar", symbol="S$", decimal_places=2, country="Singapore"),
    SupportedCurrency.HKD: CurrencyInfo(code=SupportedCurrency.HKD, name="Hong Kong Dollar", symbol="HK$", decimal_places=2, country="Hong Kong"),
    SupportedCurrency.NOK: CurrencyInfo(code=SupportedCurrency.NOK, name="Norwegian Krone", symbol="kr", decimal_places=2, country="Norway"),
    SupportedCurrency.KRW: CurrencyInfo(code=SupportedCurrency.KRW, name="South Korean Won", symbol="₩", decimal_places=0, country="South Korea"),
    SupportedCurrency.TRY: CurrencyInfo(code=SupportedCurrency.TRY, name="Turkish Lira", symbol="₺", decimal_places=2, country="Turkey"),
    SupportedCurrency.RUB: CurrencyInfo(code=SupportedCurrency.RUB, name="Russian Ruble", symbol="₽", decimal_places=2, country="Russia"),
    SupportedCurrency.INR: CurrencyInfo(code=SupportedCurrency.INR, name="Indian Rupee", symbol="₹", decimal_places=2, country="India"),
    SupportedCurrency.BRL: CurrencyInfo(code=SupportedCurrency.BRL, name="Brazilian Real", symbol="R$", decimal_places=2, country="Brazil"),
    SupportedCurrency.ZAR: CurrencyInfo(code=SupportedCurrency.ZAR, name="South African Rand", symbol="R", decimal_places=2, country="South Africa"),
}

# Base exchange rates (relative to USD)
BASE_RATES = {
    SupportedCurrency.USD: 1.0000,
    SupportedCurrency.EUR: 0.8500,
    SupportedCurrency.GBP: 0.7800,
    SupportedCurrency.JPY: 150.0000,
    SupportedCurrency.CAD: 1.3500,
    SupportedCurrency.AUD: 1.5200,
    SupportedCurrency.CHF: 0.9100,
    SupportedCurrency.CNY: 7.2500,
    SupportedCurrency.SEK: 10.5000,
    SupportedCurrency.NZD: 1.6800,
    SupportedCurrency.MXN: 17.5000,
    SupportedCurrency.SGD: 1.3600,
    SupportedCurrency.HKD: 7.8500,
    SupportedCurrency.NOK: 10.8000,
    SupportedCurrency.KRW: 1320.0000,
    SupportedCurrency.TRY: 28.5000,
    SupportedCurrency.RUB: 95.0000,
    SupportedCurrency.INR: 83.2500,
    SupportedCurrency.BRL: 5.0500,
    SupportedCurrency.ZAR: 18.7500,
}

# Mock Currency Exchange Logic

class MockCurrencyExchange:
    
    @staticmethod
    def add_market_volatility(base_rate: float, volatility: float = 0.02) -> float:
        """Add realistic market volatility to exchange rates."""
        import random
        variation = random.uniform(-volatility, volatility)
        return base_rate * (1 + variation)
    
    @staticmethod
    def calculate_spread(rate: float, spread_percent: float = 0.5) -> tuple[float, float, float]:
        """Calculate bid, ask, and mid prices with spread."""
        spread = rate * (spread_percent / 100)
        bid = rate - (spread / 2)
        ask = rate + (spread / 2)
        mid = rate
        return bid, ask, mid
    
    @staticmethod
    def get_exchange_rate(from_currency: SupportedCurrency, to_currency: SupportedCurrency, 
                         provider: ExchangeRateProvider = ExchangeRateProvider.MARKET) -> ExchangeRate:
        """Get current exchange rate between two currencies."""
        
        current_time = int(time.time())
        
        if from_currency == to_currency:
            rate = 1.0
            bid = ask = mid = rate
            spread_percent = 0.0
        else:
            # Calculate cross rate via USD
            from_usd_rate = BASE_RATES[from_currency]
            to_usd_rate = BASE_RATES[to_currency]
            base_rate = to_usd_rate / from_usd_rate
            
            # Add market volatility
            volatility = 0.01 if provider == ExchangeRateProvider.CENTRAL_BANK else 0.02
            rate = MockCurrencyExchange.add_market_volatility(base_rate, volatility)
            
            # Calculate spread based on provider
            spread_percent = {
                ExchangeRateProvider.CENTRAL_BANK: 0.1,
                ExchangeRateProvider.MARKET: 0.3,
                ExchangeRateProvider.COMMERCIAL: 0.5,
                ExchangeRateProvider.CRYPTOCURRENCY: 1.0
            }.get(provider, 0.3)
            
            bid, ask, mid = MockCurrencyExchange.calculate_spread(rate, spread_percent)
        
        return ExchangeRate(
            from_currency=from_currency,
            to_currency=to_currency,
            rate=round(rate, 6),
            inverse_rate=round(1/rate, 6) if rate != 0 else 0,
            bid=round(bid, 6),
            ask=round(ask, 6),
            mid=round(mid, 6),
            spread_percent=round(spread_percent, 2),
            provider=provider,
            timestamp=current_time,
            source=f"{provider.value}_feed",
            expires_at=current_time + 300  # 5 minutes
        )
    
    @staticmethod
    def convert_currency(request: ConversionRequest) -> ConversionResult:
        """Convert currency amount using current exchange rates."""
        
        conversion_id = f"fx_{uuid.uuid4().hex[:24]}"
        current_time = int(time.time())
        
        # Get exchange rate
        rate_info = MockCurrencyExchange.get_exchange_rate(
            request.from_currency, 
            request.to_currency, 
            request.rate_type
        )
        
        # Calculate conversion
        converted_amount = request.amount * rate_info.rate
        
        # Calculate fees (0.5% for market, 1% for commercial)
        fee_percent = {
            ExchangeRateProvider.CENTRAL_BANK: 0.1,
            ExchangeRateProvider.MARKET: 0.3,
            ExchangeRateProvider.COMMERCIAL: 0.8,
            ExchangeRateProvider.CRYPTOCURRENCY: 1.5
        }.get(request.rate_type, 0.3)
        
        fees = converted_amount * (fee_percent / 100)
        net_amount = converted_amount - fees
        
        return ConversionResult(
            id=conversion_id,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            from_amount=request.amount,
            to_amount=round(converted_amount, CURRENCY_INFO[request.to_currency].decimal_places),
            exchange_rate=rate_info.rate,
            rate_used=rate_info,
            fees=round(fees, CURRENCY_INFO[request.to_currency].decimal_places),
            net_amount=round(net_amount, CURRENCY_INFO[request.to_currency].decimal_places),
            customer_id=request.customer_id,
            reference=request.reference,
            created=current_time,
            expires_at=current_time + 1800,  # 30 minutes
            status="completed",
            metadata=request.metadata or {}
        )
    
    @staticmethod
    def generate_rate_history(from_currency: SupportedCurrency, to_currency: SupportedCurrency, 
                            days: int = 30) -> List[RateHistoryEntry]:
        """Generate realistic historical exchange rate data."""
        
        current_time = int(time.time())
        current_rate = MockCurrencyExchange.get_exchange_rate(from_currency, to_currency).rate
        
        history = []
        for i in range(days):
            timestamp = current_time - (i * 24 * 60 * 60)
            
            # Add trend and volatility
            trend_factor = 1 + (i * 0.001)  # Slight upward trend
            volatility = MockCurrencyExchange.add_market_volatility(current_rate * trend_factor, 0.015)
            
            # Generate OHLC data
            base_rate = volatility
            daily_volatility = base_rate * 0.02
            
            open_rate = MockCurrencyExchange.add_market_volatility(base_rate, 0.01)
            high_rate = base_rate + abs(daily_volatility)
            low_rate = base_rate - abs(daily_volatility)
            close_rate = MockCurrencyExchange.add_market_volatility(base_rate, 0.01)
            
            volume = random.uniform(1000000, 5000000)  # Mock trading volume
            
            history.append(RateHistoryEntry(
                timestamp=timestamp,
                rate=round(close_rate, 6),
                volume=round(volume, 2),
                high=round(high_rate, 6),
                low=round(low_rate, 6),
                open=round(open_rate, 6),
                close=round(close_rate, 6)
            ))
        
        return sorted(history, key=lambda x: x.timestamp)

# In-memory storage for demo purposes
MOCK_CONVERSIONS: Dict[str, ConversionResult] = {}

# API Endpoints

@router.get("/rates", response_model=Dict[str, ExchangeRate])
async def get_all_rates(
    base: SupportedCurrency = Query(SupportedCurrency.USD, description="Base currency for rates"),
    provider: ExchangeRateProvider = Query(ExchangeRateProvider.MARKET, description="Rate provider"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get current exchange rates for all supported currencies.
    
    Returns exchange rates from the specified base currency to all other
    supported currencies using the specified rate provider.
    """
    
    rates = {}
    for currency in SupportedCurrency:
        if currency != base:
            rate = MockCurrencyExchange.get_exchange_rate(base, currency, provider)
            rates[f"{base}/{currency}"] = rate
    
    return rates

@router.get("/rates/{from_currency}/{to_currency}", response_model=ExchangeRate)
async def get_exchange_rate(
    from_currency: SupportedCurrency,
    to_currency: SupportedCurrency,
    provider: ExchangeRateProvider = Query(ExchangeRateProvider.MARKET),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get exchange rate between two specific currencies.
    
    Returns the current exchange rate, bid/ask prices, and spread information
    for the specified currency pair.
    """
    
    rate = MockCurrencyExchange.get_exchange_rate(from_currency, to_currency, provider)
    return rate

@router.post("/convert", response_model=ConversionResult)
async def convert_currency(
    conversion_request: ConversionRequest,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.CREATE))
):
    """
    Convert currency amount using current exchange rates.
    
    This endpoint performs actual currency conversion with fee calculation
    and returns detailed conversion information.
    """
    
    conversion_result = MockCurrencyExchange.convert_currency(conversion_request)
    
    # Store in mock database
    MOCK_CONVERSIONS[conversion_result.id] = conversion_result
    
    return conversion_result

@router.get("/convert/{conversion_id}", response_model=ConversionResult)
async def get_conversion(
    conversion_id: str,
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Retrieve a specific currency conversion by ID.
    
    Returns detailed information about a previously executed conversion.
    """
    
    if conversion_id not in MOCK_CONVERSIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversion not found"
        )
    
    return MOCK_CONVERSIONS[conversion_id]

@router.get("/history/{from_currency}/{to_currency}", response_model=RateHistoryResponse)
async def get_rate_history(
    from_currency: SupportedCurrency,
    to_currency: SupportedCurrency,
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get historical exchange rate data for a currency pair.
    
    Returns time-series data including OHLC (Open, High, Low, Close) prices
    and trading volumes for the specified period.
    """
    
    history_data = MockCurrencyExchange.generate_rate_history(from_currency, to_currency, days)
    
    return RateHistoryResponse(
        from_currency=from_currency,
        to_currency=to_currency,
        period=f"{days}d",
        data=history_data,
        total_entries=len(history_data)
    )

@router.get("/currencies", response_model=Dict[str, CurrencyInfo])
async def get_supported_currencies(
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get information about all supported currencies.
    
    Returns detailed information about each supported currency including
    name, symbol, decimal places, and country information.
    """
    
    return {currency.value: info for currency, info in CURRENCY_INFO.items()}

@router.get("/analytics/summary")
async def get_fx_analytics(
    days: int = Query(30, ge=1, le=365),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get currency exchange analytics and statistics.
    
    Returns comprehensive metrics about currency conversion volumes,
    popular currency pairs, and market trends.
    """
    
    current_time = int(time.time())
    start_time = current_time - (days * 24 * 60 * 60)
    
    # Filter conversions within date range
    recent_conversions = [c for c in MOCK_CONVERSIONS.values() if c.created >= start_time]
    
    # Calculate metrics
    total_conversions = len(recent_conversions)
    total_volume = sum(c.from_amount for c in recent_conversions)
    total_fees = sum(c.fees for c in recent_conversions)
    
    # Currency pair analysis
    pair_volumes = {}
    for conversion in recent_conversions:
        pair = f"{conversion.from_currency}/{conversion.to_currency}"
        if pair not in pair_volumes:
            pair_volumes[pair] = {"count": 0, "volume": 0.0}
        pair_volumes[pair]["count"] += 1
        pair_volumes[pair]["volume"] += conversion.from_amount
    
    # Most popular pairs
    popular_pairs = sorted(pair_volumes.items(), key=lambda x: x[1]["count"], reverse=True)[:10]
    
    # Provider usage
    provider_usage = {}
    for conversion in recent_conversions:
        provider = conversion.rate_used.provider.value
        provider_usage[provider] = provider_usage.get(provider, 0) + 1
    
    # Average conversion size by currency
    currency_averages = {}
    for currency in SupportedCurrency:
        currency_conversions = [c for c in recent_conversions if c.from_currency == currency]
        if currency_conversions:
            avg_amount = sum(c.from_amount for c in currency_conversions) / len(currency_conversions)
            currency_averages[currency.value] = round(avg_amount, 2)
    
    import random
    return {
        "period_days": days,
        "total_conversions": total_conversions,
        "total_volume_usd": round(total_volume, 2),
        "total_fees_collected": round(total_fees, 2),
        "average_conversion_size": round(total_volume / total_conversions, 2) if total_conversions > 0 else 0,
        "popular_currency_pairs": [
            {"pair": pair, "conversions": data["count"], "volume": round(data["volume"], 2)}
            for pair, data in popular_pairs
        ],
        "provider_usage": provider_usage,
        "average_conversion_by_currency": currency_averages,
        "market_volatility": {
            "usd_eur": round(random.uniform(0.5, 2.0), 2),
            "usd_gbp": round(random.uniform(0.6, 2.2), 2),
            "usd_jpy": round(random.uniform(0.8, 1.8), 2)
        },
        "trending_currencies": [
            {"currency": "EUR", "trend": "up", "change_percent": 2.3},
            {"currency": "GBP", "trend": "down", "change_percent": -1.1},
            {"currency": "JPY", "trend": "up", "change_percent": 0.8}
        ]
    }

@router.get("/rates/live")
async def get_live_rates(
    pairs: str = Query(..., description="Comma-separated currency pairs (e.g., USD/EUR,GBP/USD)"),
    api_key: APIKey = Depends(require_resource_permission(ResourceType.PAYMENT, Permission.READ))
):
    """
    Get live exchange rates for specific currency pairs.
    
    Returns real-time exchange rates with timestamps for specified pairs.
    Useful for trading applications and live price feeds.
    """
    
    requested_pairs = [pair.strip().upper() for pair in pairs.split(",")]
    live_rates = {}
    
    for pair in requested_pairs:
        try:
            if "/" not in pair:
                continue
            
            from_curr, to_curr = pair.split("/")
            from_currency = SupportedCurrency(from_curr)
            to_currency = SupportedCurrency(to_curr)
            
            rate = MockCurrencyExchange.get_exchange_rate(from_currency, to_currency)
            live_rates[pair] = {
                "rate": rate.rate,
                "bid": rate.bid,
                "ask": rate.ask,
                "spread": rate.spread_percent,
                "timestamp": rate.timestamp,
                "change_24h": round(random.uniform(-5.0, 5.0), 2),  # Mock 24h change
                "volume_24h": round(random.uniform(1000000, 10000000), 2)
            }
        except (ValueError, KeyError):
            live_rates[pair] = {"error": "Invalid currency pair"}
    
    return {
        "pairs": live_rates,
        "server_time": int(time.time()),
        "update_frequency": "real-time"
    }

# Health check endpoint
@router.get("/health")
async def currency_exchange_api_health():
    """Health check for currency exchange API."""
    return {
        "status": "healthy",
        "service": "currency_exchange",
        "version": "1.0.0",
        "endpoints": [
            "GET /rates",
            "GET /rates/{from_currency}/{to_currency}",
            "POST /convert", 
            "GET /convert/{conversion_id}",
            "GET /history/{from_currency}/{to_currency}",
            "GET /currencies",
            "GET /analytics/summary",
            "GET /rates/live"
        ],
        "mock_features": [
            "Real-time exchange rates",
            "Multi-provider rate sources",
            "Historical rate data",
            "Currency conversion with fees",
            "Market volatility simulation"
        ],
        "supported_currencies": len(SupportedCurrency),
        "rate_providers": len(ExchangeRateProvider),
        "base_currencies": ["USD", "EUR", "GBP", "JPY", "CAD"]
    }