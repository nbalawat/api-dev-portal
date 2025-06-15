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
    return this.request<any[]>('/api/api-keys/')
  }

  async createApiKey(keyData: {
    name: string
    description?: string
    permissions?: string[]
    rate_limit?: number
    expires_in_days?: number
  }) {
    return this.request<any>('/api/api-keys/', {
      method: 'POST',
      body: JSON.stringify(keyData),
    })
  }

  async updateApiKey(keyId: string, updates: any) {
    return this.request<any>(`/api/api-keys/${keyId}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    })
  }

  async deleteApiKey(keyId: string) {
    return this.request<any>(`/api/api-keys/${keyId}/revoke`, {
      method: 'POST',
    })
  }

  async regenerateApiKey(keyId: string) {
    return this.request<any>(`/api/api-keys/${keyId}/rotate`, {
      method: 'POST',
    })
  }

  // Analytics
  async getUsageStats() {
    return this.request<any>('/api/ui/dashboard')
  }

  async getUsageTrends(period: string = '7d') {
    return this.request<any>(`/api/analytics/time-series`, {
      method: 'POST',
      body: JSON.stringify({ period })
    })
  }

  async getEndpointStats() {
    return this.request<any>('/api/analytics/endpoints')
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