'use client'

import { useState, useEffect } from 'react'
import React from 'react'
import Link from 'next/link'
import { AuthWrapper } from '@/components/auth-wrapper'
import { motion } from 'framer-motion'
import { 
  CreditCard,
  ArrowLeftRight,
  DollarSign,
  BarChart3,
  Shield,
  Zap,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
  Code,
  BookOpen,
  TrendingUp,
  Database,
  Banknote,
  PieChart,
  Users,
  Layers,
  Globe,
  Eye,
  Filter,
  ArrowLeft
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useApiKeys, useCurrentUser } from '@/hooks/use-api'
import { apiClient } from '@/lib/api'
import { useToast } from '@/hooks/use-toast'
import { ApiTestModal } from '@/components/marketplace/api-test-modal'
import { SearchBar, type SearchFilters } from '@/components/marketplace/search-bar'
import type { 
  MarketplaceHealth, 
  MarketplaceStatus,
  MarketplaceApiCall,
  MarketplaceCategory 
} from '@/types/marketplace'

const MARKETPLACE_CATEGORIES: MarketplaceCategory[] = [
  {
    id: 'payments',
    name: 'Payment Processing',
    description: 'Core payment processing, refunds, and transaction management',
    icon: '💳',
    phase: 1,
    apis: [
      {
        endpoint: '/marketplace/v1/payments/process',
        method: 'POST',
        requiresApiKey: true,
        description: 'Process payments with multiple payment methods',
        category: 'payments',
        phase: 1
      },
      {
        endpoint: '/marketplace/v1/payments/{payment_id}',
        method: 'GET',
        requiresApiKey: true,
        description: 'Retrieve payment details by ID',
        category: 'payments',
        phase: 1
      },
      {
        endpoint: '/marketplace/v1/refunds/create',
        method: 'POST',
        requiresApiKey: true,
        description: 'Create refunds for existing payments',
        category: 'payments',
        phase: 1
      },
      {
        endpoint: '/marketplace/v1/subscriptions/create',
        method: 'POST',
        requiresApiKey: true,
        description: 'Create recurring subscription payments',
        category: 'payments',
        phase: 1
      },
      {
        endpoint: '/marketplace/v1/transactions/search',
        method: 'POST',
        requiresApiKey: true,
        description: 'Search and filter transaction history',
        category: 'payments',
        phase: 1
      }
    ]
  },
  {
    id: 'financial',
    name: 'Financial Services',
    description: 'Bank verification, currency exchange, credit scoring, and reporting',
    icon: '🏦',
    phase: 2,
    apis: [
      {
        endpoint: '/marketplace/v1/bank-verification/initiate',
        method: 'POST',
        requiresApiKey: true,
        description: 'Initiate bank account verification process',
        category: 'financial',
        phase: 2
      },
      {
        endpoint: '/marketplace/v1/fx/rates',
        method: 'GET',
        requiresApiKey: true,
        description: 'Get real-time currency exchange rates',
        category: 'financial',
        phase: 2
      },
      {
        endpoint: '/marketplace/v1/credit/score',
        method: 'POST',
        requiresApiKey: true,
        description: 'Get credit scores and risk assessments',
        category: 'financial',
        phase: 2
      },
      {
        endpoint: '/marketplace/v1/financial-reporting/revenue-analytics',
        method: 'POST',
        requiresApiKey: true,
        description: 'Generate comprehensive revenue analytics',
        category: 'financial',
        phase: 2
      }
    ]
  }
]

export default function MarketplacePage() {
  const [activeCategory, setActiveCategory] = useState('payments')
  const [marketplaceHealth, setMarketplaceHealth] = useState<MarketplaceHealth | null>(null)
  const [marketplaceStatus, setMarketplaceStatus] = useState<MarketplaceStatus | null>(null)
  const [selectedApiKey, setSelectedApiKey] = useState<string>('')
  const [healthLoading, setHealthLoading] = useState(true)
  const [statusLoading, setStatusLoading] = useState(false)
  const [showTestModal, setShowTestModal] = useState(false)
  const [selectedApi, setSelectedApi] = useState<MarketplaceApiCall | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFilters, setSearchFilters] = useState<SearchFilters | undefined>()
  
  // Hooks
  const { data: apiKeys, loading: apiKeysLoading } = useApiKeys()
  const { data: currentUser } = useCurrentUser()
  const { toast } = useToast()

  // Debug: Log API keys to see their structure
  useEffect(() => {
    if (apiKeys) {
      console.log('API Keys data:', apiKeys)
      console.log('First API key:', apiKeys[0])
    }
  }, [apiKeys])

  // Load marketplace health on component mount
  useEffect(() => {
    loadMarketplaceHealth()
  }, [])

  // Load marketplace status when API key changes
  useEffect(() => {
    if (selectedApiKey) {
      loadMarketplaceStatus()
    }
  }, [selectedApiKey])

  const loadMarketplaceHealth = async () => {
    try {
      setHealthLoading(true)
      const health = await apiClient.getMarketplaceHealth()
      setMarketplaceHealth(health)
    } catch (error) {
      console.error('Failed to load marketplace health:', error)
      toast({
        title: 'Error',
        description: 'Failed to load marketplace health status',
        variant: 'destructive'
      })
    } finally {
      setHealthLoading(false)
    }
  }

  const loadMarketplaceStatus = async () => {
    if (!selectedApiKey) return
    
    try {
      setStatusLoading(true)
      const status = await apiClient.getMarketplaceStatus(selectedApiKey)
      setMarketplaceStatus(status)
    } catch (error) {
      console.error('Failed to load marketplace status:', error)
      toast({
        title: 'Error',
        description: 'Failed to load marketplace status. Check your API key permissions.',
        variant: 'destructive'
      })
    } finally {
      setStatusLoading(false)
    }
  }

  const getHealthStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'operational':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      case 'down':
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Activity className="h-5 w-5 text-gray-500" />
    }
  }

  const getHealthStatusVariant = (status: string): 'success' | 'warning' | 'destructive' | 'secondary' => {
    const variants = {
      healthy: 'success' as const,
      operational: 'success' as const,
      degraded: 'warning' as const,
      down: 'destructive' as const,
      error: 'destructive' as const
    }
    return variants[status as keyof typeof variants] || 'secondary' as const
  }

  const formatUptime = (uptimeSeconds: number) => {
    const days = Math.floor(uptimeSeconds / 86400)
    const hours = Math.floor((uptimeSeconds % 86400) / 3600)
    const minutes = Math.floor((uptimeSeconds % 3600) / 60)
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`
    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  const getCategoryIcon = (categoryId: string) => {
    const icons = {
      payments: <CreditCard className="h-6 w-6" />,
      financial: <Banknote className="h-6 w-6" />,
      security: <Shield className="h-6 w-6" />,
      tools: <Layers className="h-6 w-6" />
    }
    return icons[categoryId as keyof typeof icons] || <Code className="h-6 w-6" />
  }

  const getMethodBadgeVariant = (method: string): 'default' | 'success' | 'warning' | 'destructive' | 'secondary' => {
    const variants = {
      GET: 'default' as const,
      POST: 'success' as const,
      PUT: 'warning' as const,
      DELETE: 'destructive' as const
    }
    return variants[method as keyof typeof variants] || 'secondary' as const
  }

  const handleTestApi = (api: MarketplaceApiCall) => {
    if (!selectedApiKey) {
      toast({
        title: 'API Key Required',
        description: 'Please select an API key to test the API',
        variant: 'destructive'
      })
      return
    }
    
    setSelectedApi(api)
    setShowTestModal(true)
  }

  const handleSearch = (query: string, filters?: SearchFilters) => {
    setSearchQuery(query)
    setSearchFilters(filters)
  }

  const filterApis = (apis: MarketplaceApiCall[]) => {
    return apis.filter(api => {
      // Text search
      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase()
        const matchesText = 
          api.endpoint.toLowerCase().includes(searchLower) ||
          api.description.toLowerCase().includes(searchLower) ||
          api.category.toLowerCase().includes(searchLower)
        
        if (!matchesText) return false
      }

      // Filter by method
      if (searchFilters?.methods.length && !searchFilters.methods.includes(api.method)) {
        return false
      }

      // Filter by category
      if (searchFilters?.categories.length && !searchFilters.categories.includes(api.category)) {
        return false
      }

      // Filter by requires API key
      if (searchFilters?.requiresApiKey !== undefined && api.requiresApiKey !== searchFilters.requiresApiKey) {
        return false
      }

      return true
    })
  }

  return (
    <AuthWrapper>
      <div className="container mx-auto p-6 space-y-8">
        {/* Navigation Breadcrumb */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="flex items-center gap-2 text-sm text-muted-foreground"
        >
          <Link 
            href="/dashboard" 
            className="flex items-center gap-2 hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <span>/</span>
          <span className="text-foreground font-medium">API Marketplace</span>
        </motion.div>

        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center space-y-4"
        >
          <h1 className="text-4xl font-bold tracking-tight">API Marketplace</h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Explore and test our comprehensive suite of payment processing and financial services APIs. 
            Build powerful applications with enterprise-grade reliability.
          </p>
          
          {/* Getting Started Alert */}
          {(!apiKeys || apiKeys.length === 0) && !apiKeysLoading && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.5 }}
              className="max-w-2xl mx-auto"
            >
              <div className="bg-blue-500/10 dark:bg-blue-400/10 border-2 border-blue-500 dark:border-blue-400 rounded-xl p-4 text-left backdrop-blur-sm">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 mr-3 flex-shrink-0" />
                  <div>
                    <h3 className="text-sm font-semibold text-foreground mb-1">
                      Get Started with API Testing
                    </h3>
                    <p className="text-sm text-foreground/80 mb-3">
                      To test APIs in the marketplace, you need to create an API key first.
                    </p>
                    <Link 
                      href="/dashboard"
                      className="inline-flex items-center text-sm bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700 transition-colors"
                    >
                      Create API Key in Dashboard →
                    </Link>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Marketplace Health & Status Overview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
        >
          {/* Marketplace Health */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">System Health</CardTitle>
              {healthLoading ? (
                <Activity className="h-4 w-4 animate-pulse text-muted-foreground" />
              ) : (
                marketplaceHealth && getHealthStatusIcon(marketplaceHealth.status)
              )}
            </CardHeader>
            <CardContent>
              {healthLoading ? (
                <div className="space-y-2">
                  <div className="h-4 bg-muted animate-pulse rounded" />
                  <div className="h-3 bg-muted animate-pulse rounded w-3/4" />
                </div>
              ) : marketplaceHealth ? (
                <div className="space-y-2">
                  <Badge className={getHealthStatusBadge(marketplaceHealth.status)}>
                    {marketplaceHealth.status.toUpperCase()}
                  </Badge>
                  <p className="text-xs text-muted-foreground">
                    Uptime: {formatUptime(marketplaceHealth.uptime)}
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Unable to load</p>
              )}
            </CardContent>
          </Card>

          {/* API Key Selector */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">API Key</CardTitle>
              <Eye className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <select
                value={selectedApiKey}
                onChange={(e) => setSelectedApiKey(e.target.value)}
                className="w-full text-sm border rounded px-2 py-1"
                disabled={apiKeysLoading}
              >
                <option value="">Select API Key</option>
                <option value="demo-test-key-for-marketplace-testing" className="text-blue-600">
                  🧪 Demo API Key (for testing)
                </option>
                {apiKeys?.map((key: any) => (
                  <option key={key.id} value={key.secret_key || key.key || key.key_id || key.id}>
                    {key.name} ({key.status})
                  </option>
                ))}
              </select>
              {selectedApiKey ? (
                <p className="text-xs text-muted-foreground mt-1">
                  Key selected for testing
                </p>
              ) : apiKeys?.length === 0 ? (
                <div className="mt-1">
                  <p className="text-xs text-orange-600">
                    No API keys found
                  </p>
                  <Link 
                    href="/dashboard" 
                    className="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    Create an API key in Dashboard →
                  </Link>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground mt-1">
                  Select a key to test APIs
                </p>
              )}
            </CardContent>
          </Card>

          {/* Today's Requests */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Today's Requests</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="space-y-2">
                  <div className="h-6 bg-muted animate-pulse rounded" />
                  <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
                </div>
              ) : marketplaceStatus ? (
                <div className="space-y-2">
                  <div className="text-2xl font-bold">{marketplaceStatus.total_requests_today.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">
                    {marketplaceStatus.success_rate}% success rate
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Select API key</p>
              )}
            </CardContent>
          </Card>

          {/* Response Time */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              {statusLoading ? (
                <div className="space-y-2">
                  <div className="h-6 bg-muted animate-pulse rounded" />
                  <div className="h-3 bg-muted animate-pulse rounded w-1/2" />
                </div>
              ) : marketplaceStatus ? (
                <div className="space-y-2">
                  <div className="text-2xl font-bold">{marketplaceStatus.average_response_time}ms</div>
                  <p className="text-xs text-muted-foreground">
                    {marketplaceStatus.active_apis.length} APIs active
                  </p>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">Select API key</p>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Search Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className="max-w-4xl mx-auto"
        >
          <SearchBar
            onSearch={handleSearch}
            categories={MARKETPLACE_CATEGORIES.map(cat => cat.name)}
          />
        </motion.div>

        {/* API Categories */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Tabs value={activeCategory} onValueChange={setActiveCategory}>
            <TabsList className="grid w-full grid-cols-2">
              {MARKETPLACE_CATEGORIES.map((category) => (
                <TabsTrigger key={category.id} value={category.id} className="flex items-center gap-2">
                  <span>{category.icon}</span>
                  <span>{category.name}</span>
                  <Badge variant="secondary" className="text-xs">
                    Phase {category.phase}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>

            {MARKETPLACE_CATEGORIES.map((category) => (
              <TabsContent key={category.id} value={category.id} className="space-y-6 mt-6">
                {/* Category Header */}
                <div className="text-center space-y-2">
                  <div className="flex items-center justify-center gap-3">
                    {getCategoryIcon(category.id)}
                    <h2 className="text-2xl font-bold">{category.name}</h2>
                  </div>
                  <p className="text-muted-foreground">{category.description}</p>
                </div>

                {/* API Endpoints Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {filterApis(category.apis).length === 0 ? (
                    <div className="col-span-2 text-center py-12">
                      <p className="text-muted-foreground text-lg">
                        No APIs found matching your search criteria.
                      </p>
                      {(searchQuery || searchFilters) && (
                        <Button
                          variant="outline"
                          onClick={() => {
                            setSearchQuery('')
                            setSearchFilters(undefined)
                          }}
                          className="mt-4"
                        >
                          Clear Search
                        </Button>
                      )}
                    </div>
                  ) : (
                    filterApis(category.apis).map((api, index) => (
                    <motion.div
                      key={`${api.endpoint}-${api.method}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                    >
                      <Card className="card-modern hover:shadow-xl border-2 hover:border-primary/30 bg-card/95 backdrop-blur-sm transition-all duration-300 group">
                        <CardHeader>
                          <div className="flex items-start justify-between">
                            <div className="space-y-2">
                              <div className="flex items-center gap-2">
                                <Badge variant={getMethodBadgeVariant(api.method)}>
                                  {api.method}
                                </Badge>
                                {api.requiresApiKey && (
                                  <Badge variant="outline" className="text-xs">
                                    <Shield className="h-3 w-3 mr-1" />
                                    API Key Required
                                  </Badge>
                                )}
                              </div>
                              <CardTitle className="text-sm font-mono text-foreground">
                                {api.endpoint}
                              </CardTitle>
                            </div>
                            <Badge variant="secondary" className="text-xs">
                              Phase {api.phase}
                            </Badge>
                          </div>
                          <CardDescription className="text-sm">
                            {api.description}
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              className="flex-1"
                              disabled={!selectedApiKey}
                              onClick={() => handleTestApi(api)}
                            >
                              <Play className="h-4 w-4 mr-1" />
                              Test API
                            </Button>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => {
                                // This will navigate to documentation
                                toast({
                                  title: 'Documentation',
                                  description: 'API documentation coming soon'
                                })
                              }}
                            >
                              <BookOpen className="h-4 w-4" />
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    </motion.div>
                  )))}
                </div>

                {/* Category Features */}
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5" />
                      {category.name} Features
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {category.id === 'payments' && (
                        <>
                          <div className="text-center space-y-2">
                            <Zap className="h-8 w-8 mx-auto text-blue-500" />
                            <h3 className="font-semibold">Fast Processing</h3>
                            <p className="text-sm text-muted-foreground">
                              Process payments in under 2 seconds with 99.9% uptime
                            </p>
                          </div>
                          <div className="text-center space-y-2">
                            <Globe className="h-8 w-8 mx-auto text-green-500" />
                            <h3 className="font-semibold">Global Coverage</h3>
                            <p className="text-sm text-muted-foreground">
                              Accept payments from 190+ countries and territories
                            </p>
                          </div>
                          <div className="text-center space-y-2">
                            <Shield className="h-8 w-8 mx-auto text-purple-500" />
                            <h3 className="font-semibold">Secure & Compliant</h3>
                            <p className="text-sm text-muted-foreground">
                              PCI DSS Level 1 certified with fraud protection
                            </p>
                          </div>
                        </>
                      )}
                      {category.id === 'financial' && (
                        <>
                          <div className="text-center space-y-2">
                            <BarChart3 className="h-8 w-8 mx-auto text-blue-500" />
                            <h3 className="font-semibold">Real-time Analytics</h3>
                            <p className="text-sm text-muted-foreground">
                              Live financial reporting and revenue analytics
                            </p>
                          </div>
                          <div className="text-center space-y-2">
                            <ArrowLeftRight className="h-8 w-8 mx-auto text-green-500" />
                            <h3 className="font-semibold">Multi-Currency</h3>
                            <p className="text-sm text-muted-foreground">
                              Support for 150+ currencies with live exchange rates
                            </p>
                          </div>
                          <div className="text-center space-y-2">
                            <Users className="h-8 w-8 mx-auto text-purple-500" />
                            <h3 className="font-semibold">Credit Assessment</h3>
                            <p className="text-sm text-muted-foreground">
                              Advanced credit scoring and lending decisions
                            </p>
                          </div>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            ))}
          </Tabs>
        </motion.div>

        {/* Quick Start Guide */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5" />
                Quick Start Guide
              </CardTitle>
              <CardDescription>
                Get started with the API Marketplace in just a few steps
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center space-y-3">
                  <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mx-auto font-bold">
                    1
                  </div>
                  <h3 className="font-semibold">Select API Key</h3>
                  <p className="text-sm text-muted-foreground">
                    Choose an active API key from your dashboard to authenticate requests
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-10 h-10 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto font-bold">
                    2
                  </div>
                  <h3 className="font-semibold">Choose API Category</h3>
                  <p className="text-sm text-muted-foreground">
                    Browse Payment Processing or Financial Services APIs based on your needs
                  </p>
                </div>
                <div className="text-center space-y-3">
                  <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mx-auto font-bold">
                    3
                  </div>
                  <h3 className="font-semibold">Test & Integrate</h3>
                  <p className="text-sm text-muted-foreground">
                    Test APIs directly in the browser and integrate into your application
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* API Test Modal */}
        {selectedApi && (
          <ApiTestModal
            isOpen={showTestModal}
            onClose={() => {
              setShowTestModal(false)
              setSelectedApi(null)
            }}
            api={selectedApi}
            selectedApiKey={selectedApiKey}
          />
        )}
      </div>
    </AuthWrapper>
  )
}