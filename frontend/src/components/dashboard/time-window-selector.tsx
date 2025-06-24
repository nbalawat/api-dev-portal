'use client'

import { useState } from 'react'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Calendar, Clock, RefreshCw } from 'lucide-react'

export interface TimeWindow {
  value: string
  label: string
  interval: string
  description: string
}

export const TIME_WINDOWS: TimeWindow[] = [
  { value: 'hour', label: 'Last Hour', interval: 'minute', description: 'Last 60 minutes' },
  { value: 'day', label: 'Last 24 Hours', interval: 'hour', description: 'Last 24 hours' },
  { value: 'week', label: 'Last 7 Days', interval: 'day', description: 'Last 7 days' },
  { value: 'month', label: 'Last 30 Days', interval: 'day', description: 'Last 30 days' },
  { value: 'quarter', label: 'Last 90 Days', interval: 'week', description: 'Last 90 days' },
  { value: 'year', label: 'Last Year', interval: 'month', description: 'Last 365 days' },
]

interface TimeWindowSelectorProps {
  selectedWindow: string
  onWindowChange: (window: TimeWindow) => void
  showRefresh?: boolean
  onRefresh?: () => void
  loading?: boolean
}

export function TimeWindowSelector({
  selectedWindow,
  onWindowChange,
  showRefresh = true,
  onRefresh,
  loading = false
}: TimeWindowSelectorProps) {
  const currentWindow = TIME_WINDOWS.find(w => w.value === selectedWindow) || TIME_WINDOWS[1]

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2">
        <Clock className="w-4 h-4 text-muted-foreground" />
        <span className="text-sm font-medium text-foreground">Time Window:</span>
      </div>
      
      <Select
        value={selectedWindow}
        onValueChange={(value) => {
          const window = TIME_WINDOWS.find(w => w.value === value)
          if (window) onWindowChange(window)
        }}
      >
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Select time window" />
        </SelectTrigger>
        <SelectContent>
          {TIME_WINDOWS.map((window) => (
            <SelectItem key={window.value} value={window.value}>
              {window.label} - {window.description}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {showRefresh && onRefresh && (
        <Button
          variant="outline"
          size="sm"
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      )}
      
      <div className="text-xs text-muted-foreground ml-2">
        Showing data in {currentWindow.interval} intervals
      </div>
    </div>
  )
}

export function QuickTimeButtons({
  onWindowChange
}: {
  onWindowChange: (window: TimeWindow) => void
}) {
  const quickWindows = TIME_WINDOWS.slice(0, 4) // Show first 4 options

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Quick:</span>
      {quickWindows.map((window) => (
        <Button
          key={window.value}
          variant="outline"
          size="sm"
          onClick={() => onWindowChange(window)}
          className="text-xs px-3 py-1 h-7"
        >
          {window.label}
        </Button>
      ))}
    </div>
  )
}