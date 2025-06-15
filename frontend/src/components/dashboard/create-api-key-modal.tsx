'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Key, Shield, Zap, Globe, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

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

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={handleClose}
        />
        
        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto mx-4"
        >
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                  <Key className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <CardTitle>Create New API Key</CardTitle>
                  <p className="text-sm text-gray-500">Generate a new API key for your application</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={handleClose}>
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>

            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Basic Information */}
                <div className="space-y-4">
                  <h3 className="font-medium text-gray-900">Basic Information</h3>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      API Key Name *
                    </label>
                    <input
                      type="text"
                      value={formData.name}
                      onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                      placeholder="e.g., Production API, Mobile App Key"
                      className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                        errors.name ? 'border-red-300' : 'border-gray-300'
                      }`}
                    />
                    {errors.name && (
                      <p className="mt-1 text-sm text-red-600">{errors.name}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      placeholder="Optional description of what this key will be used for"
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Permissions */}
                <div className="space-y-4">
                  <h3 className="font-medium text-gray-900">Permissions</h3>
                  {errors.permissions && (
                    <p className="text-sm text-red-600">{errors.permissions}</p>
                  )}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {availablePermissions.map((permission) => {
                      const isSelected = formData.permissions.includes(permission.id)
                      return (
                        <button
                          key={permission.id}
                          type="button"
                          onClick={() => togglePermission(permission.id)}
                          className={`p-4 border-2 rounded-lg text-left transition-all ${
                            isSelected
                              ? 'border-blue-500 bg-blue-50'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <permission.icon className={`w-5 h-5 mt-0.5 ${
                              isSelected ? 'text-blue-600' : 'text-gray-400'
                            }`} />
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-gray-900">{permission.label}</span>
                                {isSelected && <Badge variant="default" className="text-xs">Selected</Badge>}
                              </div>
                              <p className="text-sm text-gray-500">{permission.description}</p>
                            </div>
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Rate Limiting */}
                <div className="space-y-4">
                  <h3 className="font-medium text-gray-900">Rate Limiting</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {rateLimitPresets.map((preset) => (
                      <button
                        key={preset.value}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, rate_limit: preset.value }))}
                        className={`p-3 border-2 rounded-lg text-center transition-all ${
                          formData.rate_limit === preset.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="font-medium text-gray-900">{preset.label}</div>
                        <div className="text-xs text-gray-500">{preset.description}</div>
                      </button>
                    ))}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Custom Rate Limit (requests per hour)
                    </label>
                    <input
                      type="number"
                      value={formData.rate_limit}
                      onChange={(e) => setFormData(prev => ({ ...prev, rate_limit: parseInt(e.target.value) || 0 }))}
                      min="1"
                      max="1000000"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                {/* Expiration */}
                <div className="space-y-4">
                  <h3 className="font-medium text-gray-900">Expiration</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {expirationOptions.map((option) => (
                      <button
                        key={option.value || 'never'}
                        type="button"
                        onClick={() => setFormData(prev => ({ ...prev, expires_in_days: option.value }))}
                        className={`p-3 border-2 rounded-lg text-center transition-all ${
                          formData.expires_in_days === option.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="font-medium text-gray-900">{option.label}</div>
                        <div className="text-xs text-gray-500">{option.description}</div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Submit Error */}
                {errors.submit && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{errors.submit}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <Button type="button" variant="outline" onClick={handleClose}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isLoading} className="btn-enterprise">
                    {isLoading ? 'Creating...' : 'Create API Key'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}