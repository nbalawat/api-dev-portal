'use client'

import { useState, useEffect } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  Filter, 
  X, 
  Search, 
  Key, 
  Globe, 
  Activity,
  Calendar,
  ChevronUp,
  ChevronDown
} from 'lucide-react'
import { useApiKeys } from '@/hooks/use-api'

export interface AnalyticsFilters {
  endpoints: string[]
  apiKeys: string[]
  methods: string[]
  statusCodes: number[]
  startDate?: Date
  endDate?: Date
}

interface AnalyticsFiltersProps {
  filters: AnalyticsFilters
  onFiltersChange: (filters: AnalyticsFilters) => void
  onReset: () => void
  collapsed?: boolean
  onToggleCollapsed: () => void
}

const HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
const STATUS_CODE_GROUPS = [
  { label: '2xx Success', values: [200, 201, 202, 204] },
  { label: '4xx Client Error', values: [400, 401, 403, 404, 422, 429] },
  { label: '5xx Server Error', values: [500, 502, 503, 504] }
]

// Mock endpoints - in real app, this would come from API
const COMMON_ENDPOINTS = [
  '/api/v1/profile',
  '/api/v1/api-key/info',
  '/api/v1/api-key/usage-stats', 
  '/api/v1/test-endpoint',
  '/api/analytics/summary',
  '/api/analytics/endpoints',
  '/health'
]

export function AnalyticsFilters({
  filters,
  onFiltersChange,
  onReset,
  collapsed = false,
  onToggleCollapsed
}: AnalyticsFiltersProps) {
  const [endpointSearch, setEndpointSearch] = useState('')
  const [selectedApiKey, setSelectedApiKey] = useState('')
  const { data: apiKeys, loading: apiKeysLoading } = useApiKeys()

  const handleToggleCollapsed = () => {
    onToggleCollapsed()
  }

  const hasActiveFilters = 
    filters.endpoints.length > 0 ||
    filters.apiKeys.length > 0 ||
    filters.methods.length > 0 ||
    filters.statusCodes.length > 0 ||
    filters.startDate ||
    filters.endDate

  const activeFilterCount = 
    filters.endpoints.length +
    filters.apiKeys.length +
    filters.methods.length +
    filters.statusCodes.length +
    (filters.startDate ? 1 : 0) +
    (filters.endDate ? 1 : 0)

  const addEndpoint = (endpoint: string) => {
    if (!filters.endpoints.includes(endpoint)) {
      onFiltersChange({
        ...filters,
        endpoints: [...filters.endpoints, endpoint]
      })
    }
    setEndpointSearch('')
  }

  const removeEndpoint = (endpoint: string) => {
    onFiltersChange({
      ...filters,
      endpoints: filters.endpoints.filter(e => e !== endpoint)
    })
  }

  const addApiKey = (keyId: string) => {
    if (keyId && !filters.apiKeys.includes(keyId)) {
      const newFilters = {
        ...filters,
        apiKeys: [...filters.apiKeys, keyId]
      }
      onFiltersChange(newFilters)
      setSelectedApiKey('') // Reset the select value
    }
  }

  const removeApiKey = (keyId: string) => {
    onFiltersChange({
      ...filters,
      apiKeys: filters.apiKeys.filter(k => k !== keyId)
    })
  }

  const toggleMethod = (method: string) => {
    const isSelected = filters.methods.includes(method)
    if (isSelected) {
      onFiltersChange({
        ...filters,
        methods: filters.methods.filter(m => m !== method)
      })
    } else {
      onFiltersChange({
        ...filters,
        methods: [...filters.methods, method]
      })
    }
  }

  const toggleStatusCodeGroup = (codes: number[]) => {
    const allSelected = codes.every(code => filters.statusCodes.includes(code))
    if (allSelected) {
      // Remove all codes from this group
      onFiltersChange({
        ...filters,
        statusCodes: filters.statusCodes.filter(code => !codes.includes(code))
      })
    } else {
      // Add all codes from this group
      const newCodes = [...filters.statusCodes]
      codes.forEach(code => {
        if (!newCodes.includes(code)) {
          newCodes.push(code)
        }
      })
      onFiltersChange({
        ...filters,
        statusCodes: newCodes
      })
    }
  }

  if (collapsed) {
    return (
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="outline"
                size="sm"
                onClick={handleToggleCollapsed}
                className="flex items-center gap-2 border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-800 font-semibold"
              >
                <Filter className="w-4 h-4" />
                Filters
                {activeFilterCount > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {activeFilterCount}
                  </Badge>
                )}
                <ChevronDown className="w-4 h-4 ml-1" />
              </Button>
              
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onReset}
                  className="text-red-600 hover:text-red-700"
                >
                  Clear All
                </Button>
              )}
            </div>
            
            {/* Active filter badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {filters.endpoints.map(endpoint => (
                <Badge key={endpoint} variant="outline" className="flex items-center gap-1">
                  <Globe className="w-3 h-3" />
                  {endpoint}
                  <X 
                    className="w-3 h-3 cursor-pointer hover:text-red-600"
                    onClick={() => removeEndpoint(endpoint)}
                  />
                </Badge>
              ))}
              {filters.apiKeys.map(keyId => {
                const apiKey = apiKeys?.find((k: any) => String(k.id) === keyId)
                return (
                  <Badge key={keyId} variant="outline" className="flex items-center gap-1">
                    <Key className="w-3 h-3" />
                    {apiKey?.name || keyId.slice(0, 8)}
                    <X 
                      className="w-3 h-3 cursor-pointer hover:text-red-600"
                      onClick={() => removeApiKey(keyId)}
                    />
                  </Badge>
                )
              })}
              {filters.methods.map(method => (
                <Badge key={method} variant="outline" className="flex items-center gap-1">
                  <Activity className="w-3 h-3" />
                  {method}
                  <X 
                    className="w-3 h-3 cursor-pointer hover:text-red-600"
                    onClick={() => toggleMethod(method)}
                  />
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Analytics Filters
            {activeFilterCount > 0 && (
              <Badge variant="secondary">
                {activeFilterCount} active
              </Badge>
            )}
          </CardTitle>
          <div className="flex items-center gap-2">
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onReset}
                className="text-red-600 hover:text-red-700"
              >
                Clear All
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleCollapsed}
              className="flex items-center gap-1 border-blue-300 bg-blue-50 hover:bg-blue-100 text-blue-800 font-semibold"
            >
              <ChevronUp className="w-4 h-4" />
              Collapse
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Endpoints Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Globe className="w-4 h-4" />
            Endpoints
          </Label>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search or enter endpoint path..."
                value={endpointSearch}
                onChange={(e) => setEndpointSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && endpointSearch.trim()) {
                    addEndpoint(endpointSearch.trim())
                  }
                }}
                className="pl-9"
              />
            </div>
            {endpointSearch.trim() && (
              <Button
                size="sm"
                onClick={() => addEndpoint(endpointSearch.trim())}
              >
                Add
              </Button>
            )}
          </div>
          
          {/* Common endpoints */}
          <div className="flex flex-wrap gap-2">
            {COMMON_ENDPOINTS.map(endpoint => (
              <Button
                key={endpoint}
                variant="outline"
                size="sm"
                onClick={() => addEndpoint(endpoint)}
                disabled={filters.endpoints.includes(endpoint)}
                className="text-xs"
              >
                {endpoint}
              </Button>
            ))}
          </div>
          
          {/* Selected endpoints */}
          {filters.endpoints.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.endpoints.map(endpoint => (
                <Badge key={endpoint} variant="default" className="flex items-center gap-1">
                  {endpoint}
                  <X 
                    className="w-3 h-3 cursor-pointer hover:text-red-200"
                    onClick={() => removeEndpoint(endpoint)}
                  />
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* API Keys Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Key className="w-4 h-4" />
            API Keys
          </Label>
          
          <Select value={selectedApiKey} onValueChange={addApiKey}>
            <SelectTrigger>
              <SelectValue placeholder="Select API key to filter..." />
            </SelectTrigger>
            <SelectContent>
              {apiKeysLoading ? (
                <SelectItem value="loading" disabled>Loading...</SelectItem>
              ) : (
                apiKeys?.map(apiKey => (
                  <SelectItem 
                    key={apiKey.id} 
                    value={String(apiKey.id)}
                    disabled={filters.apiKeys.includes(String(apiKey.id))}
                  >
                    {apiKey.name} ({apiKey.key_id})
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          
          {/* Selected API keys */}
          {filters.apiKeys.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {filters.apiKeys.map(keyId => {
                const apiKey = apiKeys?.find((k: any) => String(k.id) === keyId)
                return (
                  <Badge key={keyId} variant="default" className="flex items-center gap-1">
                    {apiKey?.name || keyId.slice(0, 8)}
                    <X 
                      className="w-3 h-3 cursor-pointer hover:text-red-200"
                      onClick={() => removeApiKey(keyId)}
                    />
                  </Badge>
                )
              })}
            </div>
          )}
        </div>

        {/* HTTP Methods Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium flex items-center gap-2">
            <Activity className="w-4 h-4" />
            HTTP Methods
          </Label>
          <div className="flex flex-wrap gap-2">
            {HTTP_METHODS.map(method => (
              <Button
                key={method}
                variant={filters.methods.includes(method) ? "default" : "outline"}
                size="sm"
                onClick={() => toggleMethod(method)}
                className="text-xs"
              >
                {method}
              </Button>
            ))}
          </div>
        </div>

        {/* Status Codes Filter */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Status Codes</Label>
          <div className="space-y-2">
            {STATUS_CODE_GROUPS.map(group => {
              const allSelected = group.values.every(code => filters.statusCodes.includes(code))
              return (
                <div key={group.label} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">{group.label}</span>
                  <Button
                    variant={allSelected ? "default" : "outline"}
                    size="sm"
                    onClick={() => toggleStatusCodeGroup(group.values)}
                    className="text-xs"
                  >
                    {allSelected ? 'Deselect' : 'Select'} All
                  </Button>
                </div>
              )
            })}
          </div>
          
          {filters.statusCodes.length > 0 && (
            <div className="text-sm text-gray-600">
              Selected: {filters.statusCodes.join(', ')}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}