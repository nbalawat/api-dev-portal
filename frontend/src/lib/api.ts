// API Client for connecting frontend to backend
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
    const formData = new FormData()
    formData.append('username', credentials.email)
    formData.append('password', credentials.password)
    
    return this.request<{ access_token: string; token_type: string }>(
      '/api/auth/login',
      {
        method: 'POST',
        headers: {},
        body: formData,
      }
    )
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
}

// Create singleton instance
export const apiClient = new ApiClient()

// Export types
export type { ApiError }
export { ApiClient }