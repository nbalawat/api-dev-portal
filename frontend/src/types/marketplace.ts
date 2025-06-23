/**
 * TypeScript interfaces for Marketplace APIs
 * Defines types for all marketplace endpoints including Phase 1 & Phase 2 APIs
 */

// ============================================================================
// GENERAL MARKETPLACE TYPES
// ============================================================================

export interface MarketplaceHealth {
  status: string
  timestamp: string
  version: string
  uptime: number
  dependencies: {
    database: string
    redis: string
    external_apis: string
  }
}

export interface MarketplaceStatus {
  service_status: string
  total_requests_today: number
  success_rate: number
  average_response_time: number
  active_apis: string[]
}

// ============================================================================
// PHASE 1: CORE PAYMENT PROCESSING APIs
// ============================================================================

// Payment Processing Types
export interface PaymentData {
  amount: number
  currency: string
  payment_method: {
    type: 'card' | 'bank_transfer' | 'digital_wallet' | 'cryptocurrency'
    details: any
  }
  customer: {
    id: string
    email: string
    name: string
  }
  description?: string
  metadata?: Record<string, any>
}

export interface Payment {
  id: string
  amount: number
  currency: string
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled'
  payment_method: {
    type: string
    details: any
  }
  customer: {
    id: string
    email: string
    name: string
  }
  description: string
  transaction_id: string
  processing_fee: number
  net_amount: number
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface PaymentListParams {
  limit?: number
  offset?: number
  status?: string
  customer_id?: string
  date_from?: string
  date_to?: string
}

export interface PaymentListResponse {
  payments: Payment[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

// Refund Types
export interface RefundData {
  payment_id: string
  amount?: number
  reason: string
  notify_customer?: boolean
  metadata?: Record<string, any>
}

export interface Refund {
  id: string
  payment_id: string
  amount: number
  currency: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  reason: string
  refund_method: string
  processing_fee: number
  net_refund_amount: number
  created_at: string
  updated_at: string
  estimated_arrival: string
  metadata: Record<string, any>
}

// Subscription Types
export interface SubscriptionData {
  customer_id: string
  plan_id: string
  payment_method_id: string
  trial_period_days?: number
  coupon_code?: string
  metadata?: Record<string, any>
}

export interface Subscription {
  id: string
  customer_id: string
  plan_id: string
  status: 'active' | 'past_due' | 'cancelled' | 'unpaid' | 'trialing'
  current_period_start: string
  current_period_end: string
  trial_start?: string
  trial_end?: string
  cancelled_at?: string
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface SubscriptionPlan {
  id: string
  name: string
  description: string
  amount: number
  currency: string
  interval: 'month' | 'year' | 'week' | 'day'
  interval_count: number
  trial_period_days: number
  active: boolean
  created_at: string
  metadata: Record<string, any>
}

export interface SubscriptionPlansResponse {
  plans: SubscriptionPlan[]
  total: number
}

// Transaction Types
export interface TransactionSearchData {
  transaction_id?: string
  payment_id?: string
  customer_id?: string
  amount_min?: number
  amount_max?: number
  currency?: string
  status?: string
  type?: 'payment' | 'refund' | 'payout' | 'adjustment'
  date_from?: string
  date_to?: string
  limit?: number
  offset?: number
}

export interface Transaction {
  id: string
  type: 'payment' | 'refund' | 'payout' | 'adjustment'
  amount: number
  currency: string
  status: string
  description: string
  reference_id: string
  customer_id: string
  payment_method: string
  processing_fee: number
  net_amount: number
  created_at: string
  settlement_date: string
  metadata: Record<string, any>
}

export interface TransactionSearchResponse {
  transactions: Transaction[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface TransactionAnalyticsParams {
  date_from?: string
  date_to?: string
  currency?: string
  group_by?: 'day' | 'week' | 'month'
}

export interface TransactionAnalytics {
  period: string
  total_volume: number
  total_count: number
  average_amount: number
  currency_breakdown: Record<string, number>
  status_breakdown: Record<string, number>
  daily_breakdown: Array<{
    date: string
    volume: number
    count: number
  }>
}

// Payment Method Types
export interface PaymentMethodData {
  customer_id: string
  type: 'card' | 'bank_account' | 'digital_wallet'
  details: any
  is_default?: boolean
  metadata?: Record<string, any>
}

export interface PaymentMethod {
  id: string
  customer_id: string
  type: 'card' | 'bank_account' | 'digital_wallet'
  details: any
  is_default: boolean
  status: 'active' | 'inactive' | 'expired'
  created_at: string
  updated_at: string
  last_used_at?: string
  metadata: Record<string, any>
}

// ============================================================================
// PHASE 2: FINANCIAL SERVICES APIs
// ============================================================================

// Bank Account Verification Types
export interface BankVerificationData {
  account_holder_name: string
  routing_number: string
  account_number: string
  account_type: 'checking' | 'savings'
  verification_method: 'micro_deposits' | 'instant'
  metadata?: Record<string, any>
}

export interface BankVerification {
  id: string
  account_holder_name: string
  routing_number: string
  account_number_last4: string
  account_type: 'checking' | 'savings'
  status: 'pending' | 'micro_deposits_sent' | 'verified' | 'failed'
  verification_method: 'micro_deposits' | 'instant'
  micro_deposits?: Array<{
    amount: number
    description: string
  }>
  verification_attempts: number
  max_attempts: number
  expires_at: string
  created_at: string
  updated_at: string
  metadata: Record<string, any>
}

export interface MicroDepositConfirmation {
  deposit_1: number
  deposit_2: number
}

export interface BankInfo {
  routing_number: string
  bank_name: string
  bank_address: string
  bank_city: string
  bank_state: string
  bank_zip: string
  wire_routing_number: string
  record_type_code: string
  last_updated: string
}

// Currency Exchange Types
export interface ExchangeRateParams {
  base_currency: string
  target_currencies?: string[]
  amount?: number
}

export interface ExchangeRate {
  base_currency: string
  target_currency: string
  rate: number
  inverse_rate: number
  last_updated: string
  provider: string
  bid: number
  ask: number
  spread: number
}

export interface ExchangeRatesResponse {
  base_currency: string
  rates: ExchangeRate[]
  timestamp: string
  provider: string
}

export interface CurrencyConversionData {
  from_currency: string
  to_currency: string
  amount: number
  rate_type?: 'real_time' | 'fixed'
}

export interface CurrencyConversion {
  from_currency: string
  to_currency: string
  from_amount: number
  to_amount: number
  exchange_rate: number
  conversion_fee: number
  net_amount: number
  rate_timestamp: string
  conversion_id: string
  expires_at: string
}

export interface CurrencyHistoryParams {
  days?: number
  interval?: 'hourly' | 'daily' | 'weekly'
  start_date?: string
  end_date?: string
}

export interface CurrencyHistoryPoint {
  timestamp: string
  rate: number
  volume?: number
  high?: number
  low?: number
  open?: number
  close?: number
}

export interface CurrencyHistory {
  from_currency: string
  to_currency: string
  data_points: CurrencyHistoryPoint[]
  period: string
  interval: string
}

// Credit Scoring Types
export interface CreditScoreData {
  customer_id: string
  ssn?: string
  date_of_birth?: string
  address: {
    street: string
    city: string
    state: string
    zip_code: string
  }
  annual_income?: number
  employment_status?: 'employed' | 'self_employed' | 'unemployed' | 'retired'
  requested_amount?: number
  purpose?: string
}

export interface CreditScore {
  customer_id: string
  score: number
  score_range: {
    min: number
    max: number
  }
  grade: 'A' | 'B' | 'C' | 'D' | 'F'
  risk_level: 'very_low' | 'low' | 'medium' | 'high' | 'very_high'
  factors: Array<{
    factor: string
    impact: 'positive' | 'negative' | 'neutral'
    description: string
  }>
  report_date: string
  expires_at: string
  provider: string
  metadata: Record<string, any>
}

export interface LendingDecisionData {
  customer_id: string
  requested_amount: number
  purpose: string
  term_months: number
  collateral_type?: string
  collateral_value?: number
}

export interface LendingDecision {
  customer_id: string
  decision: 'approved' | 'denied' | 'manual_review'
  approved_amount?: number
  interest_rate?: number
  term_months?: number
  conditions?: string[]
  denial_reasons?: string[]
  confidence_score: number
  expires_at: string
  decision_timestamp: string
  metadata: Record<string, any>
}

export interface CreditHistoryParams {
  limit?: number
  offset?: number
  date_from?: string
  date_to?: string
  event_type?: string
}

export interface CreditHistoryEvent {
  id: string
  customer_id: string
  event_type: 'score_check' | 'loan_application' | 'payment' | 'default' | 'inquiry'
  event_date: string
  description: string
  impact_score: number
  details: Record<string, any>
}

export interface CreditHistory {
  customer_id: string
  events: CreditHistoryEvent[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

// Financial Reporting Types
export interface RevenueAnalyticsData {
  date_from: string
  date_to: string
  group_by: 'day' | 'week' | 'month' | 'quarter' | 'year'
  currency?: string
  include_refunds?: boolean
  merchant_categories?: string[]
}

export interface RevenueAnalytics {
  period: string
  total_revenue: number
  net_revenue: number
  gross_revenue: number
  refunds_amount: number
  fees_amount: number
  currency: string
  breakdown: Array<{
    period: string
    gross_revenue: number
    net_revenue: number
    transaction_count: number
    average_transaction: number
    refunds_amount: number
    fees_amount: number
  }>
  growth_rate: number
  trends: {
    revenue_trend: 'increasing' | 'decreasing' | 'stable'
    transaction_trend: 'increasing' | 'decreasing' | 'stable'
  }
}

export interface ReconciliationData {
  date_from: string
  date_to: string
  include_pending?: boolean
  settlement_account_id?: string
}

export interface ReconciliationReport {
  period: string
  total_processed: number
  total_settled: number
  pending_settlement: number
  discrepancies: Array<{
    transaction_id: string
    type: 'missing_settlement' | 'amount_mismatch' | 'duplicate'
    expected_amount: number
    actual_amount: number
    description: string
  }>
  settlement_summary: Array<{
    date: string
    batch_id: string
    total_amount: number
    transaction_count: number
    status: string
  }>
  currency: string
  generated_at: string
}

export interface TaxSummaryParams {
  quarter?: number
  include_international?: boolean
  tax_type?: 'sales' | 'vat' | 'gst'
}

export interface TaxSummary {
  year: number
  quarter?: number
  total_taxable_revenue: number
  total_tax_collected: number
  tax_breakdown: Array<{
    tax_type: 'sales' | 'vat' | 'gst'
    jurisdiction: string
    rate: number
    taxable_amount: number
    tax_amount: number
  }>
  international_transactions: {
    total_amount: number
    tax_exempt_amount: number
    countries: string[]
  }
  currency: string
  generated_at: string
}

export interface CashFlowParams {
  date_from: string
  date_to: string
  group_by?: 'day' | 'week' | 'month'
  include_projections?: boolean
}

export interface CashFlowReport {
  period: string
  opening_balance: number
  closing_balance: number
  cash_inflows: Array<{
    category: string
    amount: number
    percentage: number
  }>
  cash_outflows: Array<{
    category: string
    amount: number
    percentage: number
  }>
  net_cash_flow: number
  daily_balances: Array<{
    date: string
    inflow: number
    outflow: number
    net_flow: number
    balance: number
  }>
  projections?: Array<{
    date: string
    projected_balance: number
    confidence: number
  }>
  currency: string
  generated_at: string
}

export interface FinancialDashboardMetrics {
  revenue: {
    today: number
    week: number
    month: number
    year: number
    growth_rate: number
  }
  transactions: {
    today: number
    week: number
    month: number
    success_rate: number
  }
  customers: {
    total: number
    new_this_month: number
    active_this_month: number
    churn_rate: number
  }
  payments: {
    average_amount: number
    largest_today: number
    pending_settlements: number
    failed_rate: number
  }
  top_currencies: Array<{
    currency: string
    volume: number
    percentage: number
  }>
  recent_activity: Array<{
    timestamp: string
    type: string
    description: string
    amount?: number
    currency?: string
  }>
}

// ============================================================================
// MARKETPLACE API INTEGRATION TYPES
// ============================================================================

export interface MarketplaceApiCall {
  endpoint: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  requiresApiKey: boolean
  description: string
  category: 'payments' | 'financial' | 'security' | 'tools'
  phase: 1 | 2 | 3 | 4
}

export interface MarketplaceCategory {
  id: string
  name: string
  description: string
  icon: string
  apis: MarketplaceApiCall[]
  phase: number
}

export interface ApiTestRequest {
  endpoint: string
  method: string
  headers: Record<string, string>
  body?: any
  apiKey: string
}

export interface ApiTestResponse {
  status: number
  statusText: string
  data: any
  headers: Record<string, string>
  responseTime: number
  timestamp: string
}

export interface MarketplaceAnalytics {
  total_requests: number
  success_rate: number
  average_response_time: number
  popular_endpoints: Array<{
    endpoint: string
    requests: number
    success_rate: number
  }>
  error_breakdown: Array<{
    status_code: number
    count: number
    percentage: number
  }>
  timeframe: string
}

// All interfaces are exported individually above