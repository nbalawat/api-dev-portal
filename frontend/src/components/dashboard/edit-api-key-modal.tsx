'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Key, Shield, Zap, Globe, AlertCircle, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ApiKey {
  id: string
  name: string
  key: string
  description?: string
  permissions: string[]
  rate_limit: number
  is_active: boolean
  created_at: string
  expires_at?: string
}

interface EditApiKeyModalProps {
  isOpen: boolean
  onClose: () => void
  apiKey: ApiKey | null
  onUpdateKey: (keyId: string, updates: Partial<ApiKey>) => Promise<void>
  onRegenerateKey: (keyId: string) => Promise<void>
  isLoading?: boolean
  isRegenerating?: boolean
}

export function EditApiKeyModal({ 
  isOpen, 
  onClose, 
  apiKey,
  onUpdateKey,
  onRegenerateKey,
  isLoading = false,
  isRegenerating = false
}: EditApiKeyModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [] as string[],
    rate_limit: 1000,
    is_active: true
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false)

  const availablePermissions = [
    { id: 'read', label: 'Read Access', description: 'View data and resources', icon: Globe },
    { id: 'write', label: 'Write Access', description: 'Create and update resources', icon: Zap },
    { id: 'delete', label: 'Delete Access', description: 'Remove resources', icon: AlertCircle },
    { id: 'admin', label: 'Admin Access', description: 'Full administrative control', icon: Shield }
  ]

  // Update form data when apiKey changes
  useEffect(() => {
    if (apiKey) {
      setFormData({
        name: apiKey.name,
        description: apiKey.description || '',
        permissions: apiKey.permissions,
        rate_limit: apiKey.rate_limit,
        is_active: apiKey.is_active
      })
    }
  }, [apiKey])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!apiKey) return

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
      await onUpdateKey(apiKey.id, formData)
      onClose()
    } catch (error) {
      setErrors({ submit: 'Failed to update API key. Please try again.' })
    }
  }

  const handleRegenerate = async () => {
    if (!apiKey) return
    
    try {
      await onRegenerateKey(apiKey.id)
      setShowRegenerateConfirm(false)
    } catch (error) {
      setErrors({ regenerate: 'Failed to regenerate API key. Please try again.' })
    }
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

  if (!isOpen || !apiKey) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
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
                  <CardTitle>Edit API Key</CardTitle>
                  <p className="text-sm text-gray-500">Modify settings for "{apiKey.name}"</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>

            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* API Key Display */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    API Key
                  </label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-white border border-gray-300 rounded text-sm font-mono">
                      {apiKey.key.slice(0, 12)}...{apiKey.key.slice(-8)}
                    </code>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowRegenerateConfirm(true)}
                      disabled={isRegenerating}
                    >
                      <RotateCcw className="w-4 h-4 mr-1" />
                      {isRegenerating ? 'Regenerating...' : 'Regenerate'}
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Created on {new Date(apiKey.created_at).toLocaleDateString()}
                  </p>
                </div>

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
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.is_active}
                        onChange={(e) => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                    </label>
                    <span className="text-sm font-medium text-gray-700">Active</span>
                    {!formData.is_active && (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
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
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Requests per hour
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

                {/* Errors */}
                {errors.submit && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{errors.submit}</p>
                  </div>
                )}

                {errors.regenerate && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600">{errors.regenerate}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                  <Button type="button" variant="outline" onClick={onClose}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={isLoading} className="btn-enterprise">
                    {isLoading ? 'Updating...' : 'Update API Key'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>

        {/* Regenerate Confirmation Modal */}
        {showRegenerateConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-black/50 flex items-center justify-center z-10"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="bg-white p-6 rounded-lg shadow-lg max-w-md mx-4"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Regenerate API Key?</h3>
              <p className="text-gray-600 mb-4">
                This will generate a new API key and invalidate the current one. 
                Any applications using the current key will stop working until updated.
              </p>
              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowRegenerateConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  {isRegenerating ? 'Regenerating...' : 'Regenerate Key'}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </div>
    </AnimatePresence>
  )
}