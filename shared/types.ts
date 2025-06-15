/**
 * Shared TypeScript types between frontend and backend
 * These types should match the Pydantic models in the backend
 */

// Base types
export interface BaseModel {
  id: string
  created_at: string
  updated_at: string
}

// User types
export interface User extends BaseModel {
  username: string
  email: string
  full_name: string
  bio?: string
  avatar_url?: string
  timezone?: string
  role: 'admin' | 'developer' | 'viewer'
  is_active: boolean
  email_verified: boolean
  last_login?: string
}

export interface CreateUserRequest {
  username: string
  email: string
  full_name: string
  password: string
  confirm_password: string
  role: 'admin' | 'developer' | 'viewer'
  bio?: string
  timezone?: string
}

export interface UpdateUserRequest {
  full_name?: string
  bio?: string
  avatar_url?: string
  timezone?: string
  email?: string
}

// Authentication types
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  full_name: string
  password: string
  confirm_password: string
  role?: 'developer' | 'viewer'
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface RefreshTokenRequest {
  refresh_token: string
}

// API Key types
export interface APIKey extends BaseModel {
  name: string
  description?: string
  key_id: string
  key_preview: string
  scopes: string[]
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  rate_limit_per_day?: number
  allowed_ips?: string[]
  allowed_domains?: string[]
  expires_at?: string
  is_active: boolean
  last_used?: string
  usage_count: number
  user_id: string
}

export interface CreateAPIKeyRequest {
  name: string
  description?: string
  scopes: string[]
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  rate_limit_per_day?: number
  allowed_ips?: string[]
  allowed_domains?: string[]
  expires_at?: string
}

export interface UpdateAPIKeyRequest {
  name?: string
  description?: string
  scopes?: string[]
  rate_limit_per_minute?: number
  rate_limit_per_hour?: number
  rate_limit_per_day?: number
  allowed_ips?: string[]
  allowed_domains?: string[]
  expires_at?: string
  is_active?: boolean
}

export interface APIKeyResponse extends APIKey {
  secret_key?: string // Only returned on creation
}

// Analytics types
export interface UsageStats {
  total_requests: number
  successful_requests: number
  failed_requests: number
  avg_response_time: number
  requests_by_day: TimeSeriesData[]
  requests_by_endpoint: EndpointStats[]
  error_rate: number
  most_active_keys: APIKeyUsage[]
}

export interface TimeSeriesData {
  timestamp: string
  value: number
  label?: string
}

export interface EndpointStats {
  endpoint: string
  method: string
  request_count: number
  avg_response_time: number
  error_rate: number
  last_accessed?: string
}

export interface APIKeyUsage {
  key_id: string
  key_name: string
  request_count: number
  last_used: string
  user_name: string
}

export interface AnalyticsOverview {
  total_requests: number
  requests_change: number
  success_rate: number
  success_rate_change: number
  avg_response_time: number
  response_time_change: number
  error_rate: number
  error_rate_change: number
  requests_over_time: TimeSeriesData[]
  response_times: TimeSeriesData[]
  top_endpoints: EndpointStats[]
  recent_errors: ErrorLog[]
}

export interface ErrorLog {
  timestamp: string
  endpoint: string
  method: string
  status_code: number
  error_message: string
  user_id?: string
  api_key_id?: string
}

// System types
export interface SystemStats {
  status: 'healthy' | 'warning' | 'error'
  uptime: string
  total_users: number
  users_change: number
  active_keys: number
  keys_change: number
  total_requests: number
  requests_change: number
  user_growth: TimeSeriesData[]
}

export interface SystemSettings {
  general: GeneralSettings
  security: SecuritySettings
  api: APISettings
  email: EmailSettings
  advanced: AdvancedSettings
}

export interface GeneralSettings {
  app_name: string
  app_description: string
  support_email: string
  terms_url?: string
  privacy_url?: string
}

export interface SecuritySettings {
  min_password_length: number
  require_uppercase: boolean
  require_lowercase: boolean
  require_numbers: boolean
  require_symbols: boolean
  password_expiry_days?: number
  max_login_attempts: number
  lockout_duration_minutes: number
  default_rate_limit: string
  burst_limit: number
}

export interface APISettings {
  default_rate_limit: string
  max_keys_per_user: number
  key_expiry_days?: number
  allowed_scopes: string[]
  cors_origins: string[]
}

export interface EmailSettings {
  smtp_host: string
  smtp_port: number
  smtp_user: string
  smtp_password: string
  from_email: string
  from_name: string
}

export interface AdvancedSettings {
  debug_mode: boolean
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
  metrics_enabled: boolean
  analytics_retention_days: number
}

// Activity and Audit types
export interface ActivityLog extends BaseModel {
  user_id?: string
  api_key_id?: string
  action: string
  resource_type: string
  resource_id?: string
  details: Record<string, any>
  ip_address: string
  user_agent: string
  severity: 'low' | 'medium' | 'high' | 'critical'
}

// Common response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

export interface APIError {
  detail: string
  type?: string
  code?: string
}

// Filter and query types
export interface UserFilters {
  role?: string
  status?: string
  search?: string
  page?: number
  per_page?: number
}

export interface APIKeyFilters {
  is_active?: boolean
  scope?: string
  search?: string
  page?: number
  per_page?: number
}

export interface AnalyticsFilters {
  start_date?: string
  end_date?: string
  api_key_id?: string
  endpoint?: string
  method?: string
}

// WebSocket types for real-time updates
export interface WebSocketMessage {
  type: 'stats_update' | 'new_request' | 'user_activity' | 'system_alert'
  data: any
  timestamp: string
}

export interface RealTimeStats {
  active_requests: number
  requests_per_minute: number
  avg_response_time: number
  active_users: number
  error_rate: number
}