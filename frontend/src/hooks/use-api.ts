import { useState, useEffect, useCallback } from 'react'
import { apiClient, type ApiError } from '@/lib/api'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

export function useApi<T>(
  apiCall: () => Promise<T>,
  dependencies: any[] = []
): UseApiState<T> & { refetch: () => Promise<void> } {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    
    try {
      const data = await apiCall()
      setState({ data, loading: false, error: null })
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      setState({ data: null, loading: false, error: errorMessage })
    }
  }, dependencies)

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    ...state,
    refetch: fetchData,
  }
}

// Custom hooks for specific API calls
export function useApiKeys() {
  return useApi(() => apiClient.getApiKeys())
}

export function useUsageStats() {
  return useApi(() => apiClient.getUsageStats())
}

export function useAnalyticsSummary(timeframe: string = 'day') {
  return useApi(() => apiClient.getAnalyticsSummary(timeframe), [timeframe])
}

export function useUsageTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
  return useApi(() => apiClient.getUsageTrends(timeframe, interval, filters), [timeframe, interval, filters])
}

export function useErrorTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
  return useApi(() => apiClient.getErrorTrends(timeframe, interval, filters), [timeframe, interval, filters])
}

export function useResponseTimeTrends(timeframe: string = 'week', interval: string = 'day', filters?: any) {
  return useApi(() => apiClient.getResponseTimeTrends(timeframe, interval, filters), [timeframe, interval, filters])
}

export function useEndpointStats(timeframe: string = 'day', filters?: any) {
  return useApi(() => apiClient.getEndpointStats(timeframe, filters), [timeframe, filters])
}

export function useMyApiKeyAnalytics(timeframe: string = 'week') {
  return useApi(() => apiClient.getMyApiKeyAnalytics(timeframe), [timeframe])
}

export function useAnalyticsInsights(timeframe: string = 'day') {
  return useApi(() => apiClient.getAnalyticsInsights(timeframe), [timeframe])
}

export function useCurrentUser() {
  return useApi(() => apiClient.getCurrentUser())
}

// Hook for mutations (POST, PUT, DELETE)
export function useApiMutation<T, P = any>() {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const mutate = useCallback(async (apiCall: (params: P) => Promise<T>, params: P) => {
    setState({ data: null, loading: true, error: null })
    
    try {
      const data = await apiCall(params)
      setState({ data, loading: false, error: null })
      return data
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      setState({ data: null, loading: false, error: errorMessage })
      throw error
    }
  }, [])

  return {
    ...state,
    mutate,
  }
}

// Authentication hook
export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('api_token')
    if (token) {
      apiClient.setToken(token)
      // Verify token and get user info
      apiClient.getCurrentUser()
        .then((userData) => {
          setUser(userData)
          setIsAuthenticated(true)
        })
        .catch(() => {
          apiClient.clearToken()
          setIsAuthenticated(false)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (credentials: { email: string; password: string }) => {
    try {
      const response = await apiClient.login(credentials)
      apiClient.setToken(response.access_token)
      
      const userData = await apiClient.getCurrentUser()
      setUser(userData)
      setIsAuthenticated(true)
      
      return response
    } catch (error) {
      throw error
    }
  }

  const logout = () => {
    apiClient.clearToken()
    setUser(null)
    setIsAuthenticated(false)
  }

  const register = async (userData: {
    email: string
    password: string
    full_name: string
    company?: string
  }) => {
    try {
      const response = await apiClient.register(userData)
      apiClient.setToken(response.access_token)
      setUser(response.user)
      setIsAuthenticated(true)
      return response
    } catch (error) {
      throw error
    }
  }

  return {
    isAuthenticated,
    user,
    loading,
    login,
    logout,
    register,
  }
}