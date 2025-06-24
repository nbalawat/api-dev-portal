// API Client for connecting frontend to backend
import type {
  MarketplaceHealth,
  MarketplaceStatus,
  PaymentData,
  Payment,
  PaymentListParams,
  PaymentListResponse,
  RefundData,
  Refund,
  SubscriptionData,
  Subscription,
  SubscriptionPlansResponse,
  TransactionSearchData,
  TransactionSearchResponse,
  TransactionAnalyticsParams,
  TransactionAnalytics,
  PaymentMethodData,
  PaymentMethod,
  BankVerificationData,
  BankVerification,
  MicroDepositConfirmation,
  BankInfo,
  ExchangeRateParams,
  ExchangeRatesResponse,
  CurrencyConversionData,
  CurrencyConversion,
  CurrencyHistoryParams,
  CurrencyHistory,
  CreditScoreData,
  CreditScore,
  LendingDecisionData,
  LendingDecision,
  CreditHistoryParams,
  CreditHistory,
  RevenueAnalyticsData,
  RevenueAnalytics,
  ReconciliationData,
  ReconciliationReport,
  TaxSummaryParams,
  TaxSummary,
  CashFlowParams,
  CashFlowReport,
  FinancialDashboardMetrics
} from '@/types/marketplace'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(public status: number, public message: string, public data?: any) {
    super(message)
    this.name = 'ApiError'
  }
}

interface ApiResponse<T> {
  data: T
  message?: string
  status: string
}

class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
    this.token = this.getStoredToken()
  }

  private getStoredToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('api_token')
    }
    return null
  }

  setToken(token: string) {
    this.token = token
    if (typeof window !== 'undefined') {
      localStorage.setItem('api_token', token)
    }
  }

  clearToken() {
    this.token = null
    if (typeof window !== 'undefined') {
      localStorage.removeItem('api_token')
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { Authorization: `Bearer ${this.token}` }),
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new ApiError(
          response.status,
          errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
          errorData
        )
      }

      const data = await response.json()
      return data
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      throw new ApiError(0, 'Network error or server unavailable')
    }
  }

  // Authentication
  async register(userData: {
    email: string
    password: string
    full_name: string
    company?: string
  }) {
    return this.request<{ access_token: string; token_type: string; user: any }>(
      '/api/auth/register',
      {
        method: 'POST',
        body: JSON.stringify(userData),
      }
    )
  }

  async login(credentials: { email: string; password: string }) {
    const formData = new URLSearchParams()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)
    
    const response = await fetch(`${this.baseURL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        response.status,
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        errorData
      )
    }
    
    return response.json()
  }

  async getCurrentUser() {
    return this.request<any>('/api/auth/me')
  }

  // API Keys
  async getApiKeys() {
    const response = await this.request<any>('/api/api-keys/')
    // Handle paginated response - extract the api_keys array
    return response.api_keys || response
  }

  async createApiKey(keyData: {
    name: string
    description?: string
    permissions?: string[]
    rate_limit?: number
    expires_in_days?: number
  }) {
    // Map frontend field names to backend expected names
    const payload = {
      name: keyData.name,
      description: keyData.description,
      scopes: keyData.permissions || ['read'], // Map permissions to scopes
      rate_limit: keyData.rate_limit,
      expires_in_days: keyData.expires_in_days
    }
    
    const response = await this.request<any>('/api/api-keys/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    
    // Handle response format - backend returns { api_key: {...}, secret_key: "..." }
    return response.api_key || response
  }

  async updateApiKey(keyId: string, updates: any) {
    // Map frontend field names to backend expected names
    const payload = { ...updates }
    
    // Map permissions to scopes
    if (updates.permissions) {
      payload.scopes = updates.permissions
      delete payload.permissions
    }
    
    // Map is_active to status
    if (updates.hasOwnProperty('is_active')) {
      payload.status = updates.is_active ? 'active' : 'inactive'
      delete payload.is_active
    }
    
    console.log('Updating API key with payload:', payload)
    
    return this.request<any>(`/api/api-keys/${keyId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  async deleteApiKey(keyId: string) {
    // Try the admin delete endpoint first, then fall back to revoke
    try {
      return await this.request<any>(`/api/api-keys/admin/${keyId}`, {
        method: 'DELETE',
      })
    } catch (adminError) {
      // If admin delete fails, try the revoke endpoint
      return this.request<any>(`/api/api-keys/${keyId}/revoke`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Deleted from dashboard' }),
      })
    }
  }

  async regenerateApiKey(keyId: string) {
    const response = await this.request<any>(`/api/api-keys/${keyId}/rotate`, {
      method: 'POST',
      body: JSON.stringify({ 
        new_name: undefined, // Keep original name
        copy_settings: true 
      }),
    })
    
    // Handle response format - backend might return { old_key_id, new_api_key, new_secret_key }
    return response.new_api_key || response
  }

  // Analytics
  async getUsageStats() {
    return this.request<any>('/api/ui/frontend/dashboard')
  }

  async getAnalyticsSummary(timeframe: string = 'day') {
    return this.request<any>(`/api/analytics/frontend/summary?timeframe=${timeframe}`)
  }

  async getUsageTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
    const payload: any = { 
      metric: 'requests',
      timeframe,
      interval
    }
    
    // Add filters if provided
    if (filters && (filters.endpoints?.length || filters.apiKeys?.length || filters.methods?.length || filters.statusCodes?.length)) {
      payload.filters = {}
      if (filters.endpoints?.length) payload.filters.endpoints = filters.endpoints
      if (filters.apiKeys?.length) payload.filters.api_key_ids = filters.apiKeys
      if (filters.methods?.length) payload.filters.methods = filters.methods
      if (filters.statusCodes?.length) payload.filters.status_codes = filters.statusCodes
    }
    
    return this.request<any>('/api/analytics/frontend/time-series', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getErrorTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
    const payload: any = { 
      metric: 'error_rate',
      timeframe,
      interval
    }
    
    // Add filters if provided
    if (filters && (filters.endpoints?.length || filters.apiKeys?.length || filters.methods?.length || filters.statusCodes?.length)) {
      payload.filters = {}
      if (filters.endpoints?.length) payload.filters.endpoints = filters.endpoints
      if (filters.apiKeys?.length) payload.filters.api_key_ids = filters.apiKeys
      if (filters.methods?.length) payload.filters.methods = filters.methods
      if (filters.statusCodes?.length) payload.filters.status_codes = filters.statusCodes
    }
    
    return this.request<any>('/api/analytics/frontend/time-series', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getResponseTimeTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
    const payload: any = { 
      metric: 'response_time',
      timeframe,
      interval
    }
    
    // Add filters if provided
    if (filters && (filters.endpoints?.length || filters.apiKeys?.length || filters.methods?.length || filters.statusCodes?.length)) {
      payload.filters = {}
      if (filters.endpoints?.length) payload.filters.endpoints = filters.endpoints
      if (filters.apiKeys?.length) payload.filters.api_key_ids = filters.apiKeys
      if (filters.methods?.length) payload.filters.methods = filters.methods
      if (filters.statusCodes?.length) payload.filters.status_codes = filters.statusCodes
    }
    
    return this.request<any>('/api/analytics/frontend/time-series', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getEndpointStats(timeframe: string = 'day', filters?: any) {
    const payload: any = {
      timeframe,
      limit: 20
    }
    
    // Add filters if provided
    if (filters && (filters.endpoints?.length || filters.apiKeys?.length || filters.methods?.length || filters.statusCodes?.length)) {
      payload.filters = {}
      if (filters.endpoints?.length) payload.filters.endpoints = filters.endpoints
      if (filters.apiKeys?.length) payload.filters.api_key_ids = filters.apiKeys
      if (filters.methods?.length) payload.filters.methods = filters.methods
      if (filters.statusCodes?.length) payload.filters.status_codes = filters.statusCodes
    }
    
    return this.request<any>('/api/analytics/frontend/endpoints', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async getMyApiKeyAnalytics(timeframe: string = 'week') {
    return this.request<any>(`/api/analytics/frontend/my-key?timeframe=${timeframe}`)
  }

  async getAnalyticsInsights(timeframe: string = 'day') {
    return this.request<any>(`/api/analytics/frontend/insights?timeframe=${timeframe}`)
  }

  // User Management
  async updateProfile(profileData: any) {
    return this.request<any>('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    })
  }

  async updatePreferences(preferences: any) {
    return this.request<any>('/api/users/me', {
      method: 'PUT',
      body: JSON.stringify(preferences),
    })
  }

  // Health Check
  async healthCheck() {
    return this.request<{ status: string }>('/health')
  }

  // Marketplace APIs
  async getMarketplaceHealth() {
    return this.request<MarketplaceHealth>('/marketplace/health')
  }

  async getMarketplaceStatus(apiKey: string) {
    return this.request<MarketplaceStatus>('/marketplace/status', {
      headers: { 'X-API-Key': apiKey }
    })
  }

  // Phase 1: Core Payment Processing APIs
  async processPayment(paymentData: PaymentData, apiKey: string) {
    return this.request<Payment>('/marketplace/v1/payments/process', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(paymentData)
    })
  }

  async getPayment(paymentId: string, apiKey: string) {
    return this.request<Payment>(`/marketplace/v1/payments/${paymentId}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async listPayments(params: PaymentListParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<PaymentListResponse>(`/marketplace/v1/payments/?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async createRefund(refundData: RefundData, apiKey: string) {
    return this.request<Refund>('/marketplace/v1/refunds/create', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(refundData)
    })
  }

  async getRefund(refundId: string, apiKey: string) {
    return this.request<Refund>(`/marketplace/v1/refunds/${refundId}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async createSubscription(subscriptionData: SubscriptionData, apiKey: string) {
    return this.request<Subscription>('/marketplace/v1/subscriptions/create', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(subscriptionData)
    })
  }

  async getSubscription(subscriptionId: string, apiKey: string) {
    return this.request<Subscription>(`/marketplace/v1/subscriptions/${subscriptionId}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async listSubscriptionPlans(apiKey: string) {
    return this.request<SubscriptionPlansResponse>('/marketplace/v1/subscriptions/plans/list', {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async searchTransactions(searchData: TransactionSearchData, apiKey: string) {
    return this.request<TransactionSearchResponse>('/marketplace/v1/transactions/search', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(searchData)
    })
  }

  async getTransactionAnalytics(params: TransactionAnalyticsParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<TransactionAnalytics>(`/marketplace/v1/transactions/analytics/summary?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async createPaymentMethod(paymentMethodData: PaymentMethodData, apiKey: string) {
    return this.request<PaymentMethod>('/marketplace/v1/payment-methods/create', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(paymentMethodData)
    })
  }

  async getPaymentMethod(paymentMethodId: string, apiKey: string) {
    return this.request<PaymentMethod>(`/marketplace/v1/payment-methods/${paymentMethodId}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  // Phase 2: Financial Services APIs
  async initiateBankVerification(verificationData: BankVerificationData, apiKey: string) {
    return this.request<BankVerification>('/marketplace/v1/bank-verification/initiate', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(verificationData)
    })
  }

  async confirmMicroDeposits(verificationId: string, confirmationData: MicroDepositConfirmation, apiKey: string) {
    return this.request<BankVerification>(`/marketplace/v1/bank-verification/${verificationId}/confirm`, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(confirmationData)
    })
  }

  async getBankInfo(routingNumber: string, apiKey: string) {
    return this.request<BankInfo>(`/marketplace/v1/bank-verification/routing/${routingNumber}/info`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async getExchangeRates(params: ExchangeRateParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<ExchangeRatesResponse>(`/marketplace/v1/fx/rates?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async convertCurrency(conversionData: CurrencyConversionData, apiKey: string) {
    return this.request<CurrencyConversion>('/marketplace/v1/fx/convert', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(conversionData)
    })
  }

  async getCurrencyHistory(fromCurrency: string, toCurrency: string, params: CurrencyHistoryParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<CurrencyHistory>(`/marketplace/v1/fx/history/${fromCurrency}/${toCurrency}?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async getCreditScore(creditData: CreditScoreData, apiKey: string) {
    return this.request<CreditScore>('/marketplace/v1/credit/score', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(creditData)
    })
  }

  async makeLendingDecision(lendingData: LendingDecisionData, apiKey: string) {
    return this.request<LendingDecision>('/marketplace/v1/credit/decision', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(lendingData)
    })
  }

  async getCreditHistory(customerId: string, params: CreditHistoryParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<CreditHistory>(`/marketplace/v1/credit/history/${customerId}?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async generateRevenueAnalytics(analyticsData: RevenueAnalyticsData, apiKey: string) {
    return this.request<RevenueAnalytics>('/marketplace/v1/financial-reporting/revenue-analytics', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(analyticsData)
    })
  }

  async generateReconciliationReport(reconciliationData: ReconciliationData, apiKey: string) {
    return this.request<ReconciliationReport>('/marketplace/v1/financial-reporting/reconciliation', {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: JSON.stringify(reconciliationData)
    })
  }

  async getTaxSummary(year: number, params: TaxSummaryParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<TaxSummary>(`/marketplace/v1/financial-reporting/tax-summary/${year}?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async getCashFlowReport(params: CashFlowParams, apiKey: string) {
    const query = new URLSearchParams(params as any).toString()
    return this.request<CashFlowReport>(`/marketplace/v1/financial-reporting/cash-flow?${query}`, {
      headers: { 'X-API-Key': apiKey }
    })
  }

  async getFinancialDashboardMetrics(apiKey: string) {
    return this.request<FinancialDashboardMetrics>('/marketplace/v1/financial-reporting/metrics/dashboard', {
      headers: { 'X-API-Key': apiKey }
    })
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// Export types
export type { ApiError }
export { ApiClient }