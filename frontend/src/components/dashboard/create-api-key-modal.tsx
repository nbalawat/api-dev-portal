'use client'

import { useState } from 'react'
import { Key, Shield, Zap, Globe, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'

interface CreateApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
  onCreateKey: (keyData: {
    name: string
    description: string
    permissions: string[]
    rate_limit: number
    expires_in_days?: number
  }) => Promise<void>
  isLoading?: boolean
}

export function CreateApiKeyModal({ 
  isOpen, 
  onClose, 
  onCreateKey, 
  isLoading = false 
}: CreateApiKeyModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [] as string[],
    rate_limit: 1000,
    expires_in_days: undefined as number | undefined
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const availablePermissions = [
    { id: 'read', label: 'Read Access', description: 'View data and resources', icon: Globe },
    { id: 'write', label: 'Write Access', description: 'Create and update resources', icon: Zap },
    { id: 'delete', label: 'Delete Access', description: 'Remove resources', icon: AlertCircle },
    { id: 'admin', label: 'Admin Access', description: 'Full administrative control', icon: Shield }
  ]

  const rateLimitPresets = [
    { value: 100, label: '100/hour', description: 'Development' },
    { value: 1000, label: '1,000/hour', description: 'Standard' },
    { value: 10000, label: '10,000/hour', description: 'Premium' },
    { value: 100000, label: '100,000/hour', description: 'Enterprise' }
  ]

  const expirationOptions = [
    { value: undefined, label: 'Never', description: 'No expiration' },
    { value: 30, label: '30 days', description: 'Recommended for testing' },
    { value: 90, label: '90 days', description: 'Quarterly renewal' },
    { value: 365, label: '1 year', description: 'Annual renewal' }
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validation
    const newErrors: Record<string, string> = {}
    if (!formData.name.trim()) newErrors.name = 'API key name is required'
    if (formData.name.length > 50) newErrors.name = 'Name must be 50 characters or less'
    if (formData.permissions.length === 0) newErrors.permissions = 'At least one permission is required'
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors)
      return
    }

    try {
      await onCreateKey(formData)
      onClose()
      resetForm()
    } catch (error) {
      setErrors({ submit: 'Failed to create API key. Please try again.' })
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      permissions: [],
      rate_limit: 1000,
      expires_in_days: undefined
    })
    setErrors({})
  }

  const handleClose = () => {
    onClose()
    resetForm()
  }

  const togglePermission = (permission: string) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter(p => p !== permission)
        : [...prev.permissions, permission]
    }))
    if (errors.permissions) {
      setErrors(prev => ({ ...prev, permissions: '' }))
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <Key className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <DialogTitle>Create New API Key</DialogTitle>
              <DialogDescription>Generate a new API key for your application</DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="mt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="space-y-3">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100">Basic Information</h3>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">API Key Name *</Label>
                  <Input
                    id="name"
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Production API"
                    className={errors.name ? 'border-red-500 dark:border-red-600' : ''}
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name}</p>
                  )}
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Optional description"
                  />
                </div>
              </div>
            </div>

            {/* Permissions */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">Permissions</h3>
                {errors.permissions && (
                  <p className="text-sm text-red-600 dark:text-red-400">{errors.permissions}</p>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {availablePermissions.map((permission) => {
                  const isSelected = formData.permissions.includes(permission.id)
                  return (
                    <button
                      key={permission.id}
                      type="button"
                      onClick={() => togglePermission(permission.id)}
                      className={`p-3 border rounded-lg text-left transition-all ${
                        isSelected
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <permission.icon className={`w-4 h-4 ${
                          isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'
                        }`} />
                        <div className="flex-1 min-w-0">
                          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 block truncate">{permission.label}</span>
                          {isSelected && <Badge variant="default" className="text-xs mt-1">Selected</Badge>}
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Rate Limiting & Expiration */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-3">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">Rate Limiting</h3>
                <div className="grid grid-cols-2 gap-2">
                {rateLimitPresets.map((preset) => (
                  <button
                    key={preset.value}
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, rate_limit: preset.value }))}
                    className={`p-3 border rounded-lg text-center transition-all h-16 flex flex-col justify-center ${
                      formData.rate_limit === preset.value
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{preset.label}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{preset.description}</div>
                  </button>
                ))}
                </div>
                <div>
                  <Label htmlFor="rate-limit">Custom Rate Limit</Label>
                  <Input
                    id="rate-limit"
                    type="number"
                    value={formData.rate_limit}
                    onChange={(e) => setFormData(prev => ({ ...prev, rate_limit: parseInt(e.target.value) || 0 }))}
                    min="1"
                    max="1000000"
                    placeholder="requests/hour"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100">Expiration</h3>
                <div className="grid grid-cols-2 gap-2">
                  {expirationOptions.map((option) => (
                    <button
                      key={option.value || 'never'}
                      type="button"
                      onClick={() => setFormData(prev => ({ ...prev, expires_in_days: option.value }))}
                      className={`p-3 border rounded-lg text-center transition-all h-16 flex flex-col justify-center ${
                        formData.expires_in_days === option.value
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                      }`}
                    >
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">{option.label}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">{option.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Submit Error */}
            {errors.submit && (
              <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <p className="text-sm text-red-600 dark:text-red-400">{errors.submit}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Creating...' : 'Create API Key'}
              </Button>
            </div>
          </form>
        </div>
      </DialogContent>
    </Dialog>
  )
}