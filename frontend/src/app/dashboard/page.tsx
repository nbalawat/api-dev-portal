'use client'

import { useState, useEffect } from 'react'
import { AuthWrapper } from '@/components/auth-wrapper'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  Key, 
  Users, 
  Activity, 
  Settings, 
  Plus,
  Eye,
  EyeOff,
  Copy,
  Trash2,
  Calendar,
  TrendingUp,
  Shield,
  Clock,
  Loader2,
  AlertCircle
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useApiKeys, useUsageStats, useCurrentUser, useApiMutation } from '@/hooks/use-api'
import { apiClient } from '@/lib/api'
import { toast } from '@/hooks/use-toast'
import { CreateApiKeyModal } from '@/components/dashboard/create-api-key-modal'
import { EditApiKeyModal } from '@/components/dashboard/edit-api-key-modal'

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState('overview')
  const [showApiKey, setShowApiKey] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedApiKey, setSelectedApiKey] = useState<any>(null)

  // API data hooks
  const { data: apiKeys, loading: apiKeysLoading, error: apiKeysError, refetch: refetchApiKeys } = useApiKeys()
  const { data: usageStats, loading: statsLoading, error: statsError } = useUsageStats()
  const { data: currentUser, loading: userLoading, error: userError } = useCurrentUser()
  const { mutate: deleteKeyMutate, loading: deleteLoading } = useApiMutation()
  const { mutate: createKeyMutate, loading: createLoading } = useApiMutation()
  const { mutate: updateKeyMutate, loading: updateLoading } = useApiMutation()
  const { mutate: regenerateKeyMutate, loading: regenerateLoading } = useApiMutation()

  // Check if backend is available
  const [backendStatus, setBackendStatus] = useState<'checking' | 'available' | 'unavailable'>('checking')
  
  useEffect(() => {
    const checkBackend = async () => {
      try {
        await apiClient.healthCheck()
        setBackendStatus('available')
      } catch (error) {
        setBackendStatus('unavailable')
      }
    }
    checkBackend()
  }, [])

  // Mock data fallback when backend is unavailable
  const mockStats = [
    { label: 'Total API Calls', value: '2.4M', change: '+12%', trend: 'up' },
    { label: 'Active API Keys', value: '8', change: '+2', trend: 'up' },
    { label: 'Response Time', value: '94ms', change: '-5ms', trend: 'down' },
    { label: 'Success Rate', value: '99.9%', change: '+0.1%', trend: 'up' }
  ]

  const mockApiKeys = [
    {
      id: '1',
      name: 'Production API',
      key: 'sk_prod_1234567890abcdef',
      key_id: 'ak_prod_1234567890abcdef',
      created_at: '2024-01-15T00:00:00Z',
      last_used_at: '2024-06-15T10:00:00Z',
      total_requests: 1200000,
      is_active: true,
      status: 'active',
      permissions: ['read', 'write']
    },
    {
      id: '2', 
      name: 'Development API',
      key: 'sk_dev_abcdef1234567890',
      key_id: 'ak_dev_abcdef1234567890',
      created_at: '2024-01-10T00:00:00Z',
      last_used_at: '2024-06-15T11:55:00Z',
      total_requests: 450000,
      is_active: true,
      status: 'active',
      permissions: ['read']
    }
  ]

  const mockActivity = [
    { action: 'API Key Created', key: 'Development API', time: '2 hours ago' },
    { action: 'Rate Limit Updated', key: 'Production API', time: '4 hours ago' },
    { action: 'API Call Spike', key: 'Production API', time: '6 hours ago' },
    { action: 'Key Regenerated', key: 'Testing API', time: '1 day ago' }
  ]

  // Use real data if available, otherwise fallback to mock data
  const displayStats = Array.isArray(usageStats) ? usageStats : mockStats
  const displayApiKeys = Array.isArray(apiKeys) ? apiKeys.map((key: any) => ({
    ...key,
    permissions: key.scopes || key.permissions || ['read'], // Map scopes to permissions for frontend
    key: key.key_id || key.key, // Map key_id to key for display
    last_used: key.last_used_at || key.last_used, // Map last_used_at to last_used
    is_active: key.status === 'active' // Map status to is_active
  })) : mockApiKeys
  const displayActivity = mockActivity // Always use mock for now

  const navigation = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'api-keys', label: 'API Keys', icon: Key },
    { id: 'analytics', label: 'Analytics', icon: Activity },
    { id: 'settings', label: 'Settings', icon: Settings }
  ]

  const maskApiKey = (key: string) => {
    return key.slice(0, 8) + '...' + key.slice(-4)
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      toast({
        title: "Copied!",
        description: "API key copied to clipboard",
        variant: "default",
      })
    } catch (err) {
      toast({
        title: "Error",
        description: "Failed to copy to clipboard",
        variant: "destructive",
      })
    }
  }

  const handleDeleteApiKey = async (keyId: string) => {
    try {
      await deleteKeyMutate(
        (id: string) => apiClient.deleteApiKey(id),
        keyId
      )
      toast({
        title: "Success",
        description: "API key deleted successfully",
        variant: "default",
      })
      refetchApiKeys()
    } catch (error) {
      toast({
        title: "Error", 
        description: "Failed to delete API key",
        variant: "destructive",
      })
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M'
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K'
    }
    return num.toString()
  }

  const getTimeAgo = (dateString: string) => {
    const now = new Date()
    const date = new Date(dateString)
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (diffInSeconds < 60) return 'just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
    return `${Math.floor(diffInSeconds / 86400)} days ago`
  }

  // API Key handlers
  const handleCreateApiKey = async (keyData: {
    name: string
    description: string
    permissions: string[]
    rate_limit: number
    expires_in_days?: number
  }) => {
    try {
      await createKeyMutate(
        (data: any) => apiClient.createApiKey(data),
        keyData
      )
      toast({
        title: "Success",
        description: "API key created successfully",
        variant: "default",
      })
      refetchApiKeys()
      setShowCreateModal(false)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create API key",
        variant: "destructive",
      })
      throw error
    }
  }

  const handleUpdateApiKey = async (keyId: string, updates: any) => {
    try {
      await updateKeyMutate(
        ({ id, data }: { id: string; data: any }) => apiClient.updateApiKey(id, data),
        { id: keyId, data: updates }
      )
      toast({
        title: "Success",
        description: "API key updated successfully",
        variant: "default",
      })
      refetchApiKeys()
      setShowEditModal(false)
      setSelectedApiKey(null)
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update API key",
        variant: "destructive",
      })
      throw error
    }
  }

  const handleRegenerateApiKey = async (keyId: string) => {
    try {
      await regenerateKeyMutate(
        (id: string) => apiClient.regenerateApiKey(id),
        keyId
      )
      toast({
        title: "Success",
        description: "API key regenerated successfully",
        variant: "default",
      })
      refetchApiKeys()
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to regenerate API key",
        variant: "destructive",
      })
      throw error
    }
  }

  const handleEditApiKey = (apiKey: any) => {
    setSelectedApiKey(apiKey)
    setShowEditModal(true)
  }

  return (
    <AuthWrapper>
      <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
                {/* Backend Status Indicator */}
                <div className="flex items-center gap-2">
                  {backendStatus === 'checking' && (
                    <div className="flex items-center text-yellow-600">
                      <Loader2 className="w-4 h-4 animate-spin mr-1" />
                      <span className="text-xs">Checking...</span>
                    </div>
                  )}
                  {backendStatus === 'available' && (
                    <div className="flex items-center text-green-600">
                      <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                      <span className="text-xs">Connected</span>
                    </div>
                  )}
                  {backendStatus === 'unavailable' && (
                    <div className="flex items-center text-red-600">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      <span className="text-xs">Backend Offline</span>
                    </div>
                  )}
                </div>
              </div>
              <p className="text-gray-600">
                {backendStatus === 'unavailable' 
                  ? 'Showing demo data - backend is not connected'
                  : 'Manage your API keys and monitor usage'
                }
              </p>
            </div>
            <Button 
              className="btn-enterprise" 
              disabled={backendStatus === 'unavailable'}
              onClick={() => setShowCreateModal(true)}
            >
              <Plus className="w-4 h-4 mr-2" />
              New API Key
            </Button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Sidebar Navigation */}
          <aside className="w-64 flex-shrink-0">
            <nav className="space-y-2">
              {navigation.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center px-4 py-3 text-left rounded-lg transition-colors ${
                    activeTab === item.id
                      ? 'bg-blue-100 text-blue-700 border-l-4 border-blue-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <item.icon className="w-5 h-5 mr-3" />
                  {item.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {activeTab === 'overview' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                {/* Stats Grid */}
                {statsLoading ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    {[1,2,3,4].map((i) => (
                      <Card key={i}>
                        <CardContent className="p-6">
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    {displayStats.map((stat: any, index: number) => (
                      <Card key={stat.label}>
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                              <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                            </div>
                            <div className={`flex items-center text-sm ${
                              stat.trend === 'up' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              <TrendingUp className="w-4 h-4 mr-1" />
                              {stat.change}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {/* Recent Activity */}
                <Card className="mb-8">
                  <CardHeader>
                    <CardTitle>Recent Activity</CardTitle>
                    <CardDescription>Latest API key and usage activity</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {displayActivity.map((activity: any, index: number) => (
                        <div key={index} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                          <div className="flex items-center">
                            <div className="w-2 h-2 bg-blue-600 rounded-full mr-3"></div>
                            <div>
                              <p className="font-medium text-gray-900">{activity.action}</p>
                              <p className="text-sm text-gray-500">{activity.key}</p>
                            </div>
                          </div>
                          <span className="text-sm text-gray-500">{activity.time}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {activeTab === 'api-keys' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold text-gray-900">API Keys</h2>
                  <Button 
                    className="btn-enterprise"
                    disabled={backendStatus === 'unavailable'}
                    onClick={() => setShowCreateModal(true)}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create New Key
                  </Button>
                </div>

                {apiKeysLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                    <span className="ml-2 text-gray-600">Loading API keys...</span>
                  </div>
                ) : apiKeysError ? (
                  <Card>
                    <CardContent className="p-6">
                      <div className="text-center py-8">
                        <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to load API keys</h3>
                        <p className="text-gray-500 mb-4">{apiKeysError}</p>
                        <Button onClick={refetchApiKeys} variant="outline">
                          Try Again
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-4">
                    {displayApiKeys.map((apiKey: any) => (
                      <Card key={apiKey.id}>
                        <CardContent className="p-6">
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center mb-2">
                                <h3 className="font-semibold text-gray-900 mr-3">{apiKey.name}</h3>
                                <Badge variant={apiKey.is_active ? 'default' : 'secondary'}>
                                  {apiKey.is_active ? 'active' : 'inactive'}
                                </Badge>
                              </div>
                              <div className="flex items-center space-x-4 text-sm text-gray-500">
                                <span className="flex items-center">
                                  <Calendar className="w-4 h-4 mr-1" />
                                  Created {formatDate(apiKey.created_at)}
                                </span>
                                <span className="flex items-center">
                                  <Clock className="w-4 h-4 mr-1" />
                                  Last used {getTimeAgo(apiKey.last_used)}
                                </span>
                                <span className="flex items-center">
                                  <BarChart3 className="w-4 h-4 mr-1" />
                                  {formatNumber(apiKey.total_requests)} calls
                                </span>
                              </div>
                              <div className="mt-3 flex items-center">
                                <code className="bg-gray-100 px-3 py-1 rounded text-sm font-mono">
                                  {showApiKey === apiKey.id ? apiKey.key : maskApiKey(apiKey.key)}
                                </code>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setShowApiKey(showApiKey === apiKey.id ? null : apiKey.id)}
                                  className="ml-2"
                                >
                                  {showApiKey === apiKey.id ? (
                                    <EyeOff className="w-4 h-4" />
                                  ) : (
                                    <Eye className="w-4 h-4" />
                                  )}
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => copyToClipboard(apiKey.key)}
                                  className="ml-1"
                                >
                                  <Copy className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                            <div className="flex items-center space-x-2">
                              <Button 
                                variant="outline" 
                                size="sm" 
                                disabled={backendStatus === 'unavailable'}
                                onClick={() => handleEditApiKey(apiKey)}
                              >
                                Edit
                              </Button>
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="text-red-600 hover:text-red-700"
                                onClick={() => handleDeleteApiKey(apiKey.id)}
                                disabled={deleteLoading || backendStatus === 'unavailable'}
                              >
                                {deleteLoading ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <Trash2 className="w-4 h-4" />
                                )}
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'analytics' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Analytics</h2>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                  <Card>
                    <CardHeader>
                      <CardTitle>API Usage Trends</CardTitle>
                      <CardDescription>Daily API call volume over the past week</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-72 w-full bg-gray-50 rounded-lg flex items-center justify-center">
                        <div className="text-center">
                          <BarChart3 className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                          <p className="text-sm text-gray-500">Chart placeholder</p>
                          <p className="text-xs text-gray-400">Recharts integration needed</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Error Rate</CardTitle>
                      <CardDescription>API error trends and patterns</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="h-72 w-full bg-gray-50 rounded-lg flex items-center justify-center">
                        <div className="text-center">
                          <Activity className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                          <p className="text-sm text-gray-500">Error chart placeholder</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Top Endpoints</CardTitle>
                      <CardDescription>Most frequently used API endpoints</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {[
                          { endpoint: '/api/users', percentage: 35, calls: '847K' },
                          { endpoint: '/api/auth', percentage: 25, calls: '605K' },
                          { endpoint: '/api/data', percentage: 20, calls: '484K' },
                          { endpoint: '/api/files', percentage: 12, calls: '290K' },
                          { endpoint: '/api/search', percentage: 8, calls: '194K' }
                        ].map((item, index) => (
                          <div key={index} className="flex items-center justify-between">
                            <div className="flex-1">
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-sm font-medium text-gray-900">{item.endpoint}</span>
                                <span className="text-sm text-gray-500">{item.calls}</span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div 
                                  className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                                  style={{ width: `${item.percentage}%` }}
                                ></div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="lg:col-span-2">
                    <CardHeader>
                      <CardTitle>Response Time Distribution</CardTitle>
                      <CardDescription>API response time performance metrics</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-4 gap-4">
                        {[
                          { label: 'Fast (<100ms)', value: '68%', color: 'bg-green-500' },
                          { label: 'Good (100-300ms)', value: '22%', color: 'bg-blue-500' },
                          { label: 'Slow (300-1s)', value: '8%', color: 'bg-yellow-500' },
                          { label: 'Very Slow (>1s)', value: '2%', color: 'bg-red-500' }
                        ].map((metric, index) => (
                          <div key={index} className="text-center">
                            <div className={`w-12 h-12 ${metric.color} rounded-full mx-auto mb-2 flex items-center justify-center`}>
                              <span className="text-white font-semibold text-sm">{metric.value}</span>
                            </div>
                            <p className="text-xs text-gray-600">{metric.label}</p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <h2 className="text-xl font-semibold text-gray-900 mb-6">Settings</h2>
                
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>Account Information</CardTitle>
                      <CardDescription>Manage your account details and preferences</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                          <input 
                            type="text" 
                            defaultValue="John Developer" 
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
                          <input 
                            type="email" 
                            defaultValue="john@company.com" 
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Company</label>
                          <input 
                            type="text" 
                            defaultValue="Acme Corp" 
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                          <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                            <option>Lead Developer</option>
                            <option>Backend Developer</option>
                            <option>Frontend Developer</option>
                            <option>DevOps Engineer</option>
                          </select>
                        </div>
                      </div>
                      <div className="mt-6">
                        <Button className="btn-enterprise">Save Changes</Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>API Preferences</CardTitle>
                      <CardDescription>Configure your API usage preferences</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-gray-900">Email Notifications</h4>
                            <p className="text-sm text-gray-500">Receive email alerts for API events</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" className="sr-only peer" defaultChecked />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-gray-900">Rate Limit Alerts</h4>
                            <p className="text-sm text-gray-500">Get notified when approaching rate limits</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" className="sr-only peer" defaultChecked />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>

                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-medium text-gray-900">Error Monitoring</h4>
                            <p className="text-sm text-gray-500">Monitor and alert on API errors</p>
                          </div>
                          <label className="relative inline-flex items-center cursor-pointer">
                            <input type="checkbox" className="sr-only peer" />
                            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                          </label>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>Security</CardTitle>
                      <CardDescription>Manage your account security settings</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div>
                          <Button variant="outline" className="mr-3">Change Password</Button>
                          <Button variant="outline">Enable 2FA</Button>
                        </div>
                        <div className="pt-4 border-t border-gray-200">
                          <h4 className="font-medium text-gray-900 mb-2">API Key Security</h4>
                          <p className="text-sm text-gray-500 mb-3">Configure security settings for your API keys</p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">Default Key Expiration</label>
                              <select className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                <option>Never</option>
                                <option>30 days</option>
                                <option>90 days</option>
                                <option>1 year</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">IP Whitelist</label>
                              <input 
                                type="text" 
                                placeholder="192.168.1.0/24, 10.0.0.0/8"
                                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </motion.div>
            )}
          </main>
        </div>
      </div>

      {/* Modals */}
      <CreateApiKeyModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreateKey={handleCreateApiKey}
        isLoading={createLoading}
      />

      <EditApiKeyModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        apiKey={selectedApiKey}
        onUpdateKey={handleUpdateApiKey}
        onRegenerateKey={handleRegenerateApiKey}
        isLoading={updateLoading}
        isRegenerating={regenerateLoading}
      />
      </div>
    </AuthWrapper>
  )
}