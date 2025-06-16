'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import { useUsageTrends, useErrorTrends, useEndpointStats, useResponseTimeTrends } from '@/hooks/use-api'
import { Loader2 } from 'lucide-react'
import { useMemo } from 'react'

interface ChartFilters {
  endpoints?: string[]
  apiKeys?: string[]
  methods?: string[]
  statusCodes?: number[]
}

// Color palette for charts
const CHART_COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#84cc16']

// Helper function to format date labels based on interval
function formatDateLabel(timestamp: string, interval: string): string {
  const date = new Date(timestamp)
  
  switch (interval) {
    case 'minute':
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    case 'hour':
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    case 'day':
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    case 'week':
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    case 'month':
      return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
    default:
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
}

export function UsageChart({ 
  timeframe = 'week', 
  interval = 'day',
  filters
}: { 
  timeframe?: string
  interval?: string  
  filters?: ChartFilters
}) {
  const { data: usageData, loading, error } = useUsageTrends(timeframe, interval, filters)

  const chartData = useMemo(() => {
    if (!usageData?.data) return []
    
    return usageData.data.map((item: any) => ({
      name: formatDateLabel(item.timestamp, interval),
      calls: item.value || 0,
      timestamp: item.timestamp
    }))
  }, [usageData, interval])

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !chartData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">{error || 'No usage data available'}</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip 
          formatter={(value: any) => [value, 'API Calls']}
          labelFormatter={(label) => label}
        />
        <Bar dataKey="calls" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ErrorChart({ 
  timeframe = 'week', 
  interval = 'day',
  filters
}: { 
  timeframe?: string
  interval?: string
  filters?: ChartFilters
}) {
  const { data: errorData, loading, error } = useErrorTrends(timeframe, interval, filters)

  const chartData = useMemo(() => {
    if (!errorData?.data) return []
    
    return errorData.data.map((item: any) => ({
      name: formatDateLabel(item.timestamp, interval),
      errors: item.value || 0,
      timestamp: item.timestamp
    }))
  }, [errorData, interval])

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !chartData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">{error || 'No error data available'}</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip 
          formatter={(value: any) => [value + '%', 'Error Rate']}
          labelFormatter={(label) => label}
        />
        <Line 
          type="monotone" 
          dataKey="errors" 
          stroke="#ef4444" 
          strokeWidth={2}
          dot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function EndpointChart({ 
  timeframe = 'day',
  filters
}: { 
  timeframe?: string
  filters?: ChartFilters
}) {
  const { data: endpointData, loading, error } = useEndpointStats(timeframe, filters)

  const chartData = useMemo(() => {
    if (!endpointData) return []
    
    return endpointData.slice(0, 5).map((item: any, index: number) => ({
      name: item.endpoint,
      value: item.total_requests,
      color: CHART_COLORS[index % CHART_COLORS.length]
    }))
  }, [endpointData])

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !chartData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">{error || 'No endpoint data available'}</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          outerRadius={80}
          dataKey="value"
          label={({ name, percent }) => `${name.split('/').pop()} ${(percent * 100).toFixed(0)}%`}
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip 
          formatter={(value: any) => [value, 'Requests']}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// New response time chart component
export function ResponseTimeChart({ 
  timeframe = 'week', 
  interval = 'day',
  filters
}: { 
  timeframe?: string
  interval?: string
  filters?: ChartFilters
}) {
  const { data: responseTimeData, loading, error } = useResponseTimeTrends(timeframe, interval, filters)

  const chartData = useMemo(() => {
    if (!responseTimeData?.data) return []
    
    return responseTimeData.data.map((item: any) => ({
      name: formatDateLabel(item.timestamp, interval),
      responseTime: item.value || 0,
      timestamp: item.timestamp
    }))
  }, [responseTimeData, interval])

  if (loading) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || !chartData.length) {
    return (
      <div className="h-[300px] flex items-center justify-center">
        <p className="text-gray-500 text-sm">{error || 'No response time data available'}</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip 
          formatter={(value: any) => [value + 'ms', 'Response Time']}
          labelFormatter={(label) => label}
        />
        <Line 
          type="monotone" 
          dataKey="responseTime" 
          stroke="#10b981" 
          strokeWidth={2}
          dot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}