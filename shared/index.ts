// Export all shared types and utilities
export * from './types'

// Shared constants
export const API_SCOPES = [
  'read',
  'write', 
  'admin',
  'analytics',
  'user_management',
  'api_management'
] as const

export const USER_ROLES = [
  'admin',
  'developer', 
  'viewer'
] as const

export const RATE_LIMIT_PERIODS = [
  'minute',
  'hour',
  'day'
] as const

// Utility functions that can be shared
export const formatApiKey = (key: string): string => {
  if (key.length < 8) return key
  return `${key.slice(0, 8)}${'•'.repeat(32)}${key.slice(-4)}`
}

export const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`
}