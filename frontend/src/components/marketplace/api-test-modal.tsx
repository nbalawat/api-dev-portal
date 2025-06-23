'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api'
import {
  Play,
  Copy,
  Code,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Eye,
  EyeOff,
  Download,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import type { 
  MarketplaceApiCall,
  ApiTestRequest,
  ApiTestResponse 
} from '@/types/marketplace'

interface ApiTestModalProps {
  isOpen: boolean
  onClose: () => void
  api: MarketplaceApiCall
  selectedApiKey: string
}

interface TestResult {
  success: boolean
  response: ApiTestResponse | null
  error: string | null
}

// Sample request bodies for different API endpoints
const getSampleRequestBody = (endpoint: string, method: string) => {
  const samples: Record<string, any> = {
    '/marketplace/v1/payments/process': {
      amount: 2500,
      currency: 'USD',
      customer_id: 'cust_test_123',
      payment_method: {
        type: 'card',
        card: {
          number: '4242424242424242',
          exp_month: 12,
          exp_year: 2025,
          cvc: '123',
          cardholder_name: 'Test Customer'
        }
      },
      customer: {
        id: 'cust_test_123',
        email: 'test@example.com',
        name: 'Test Customer'
      },
      description: 'Test payment from API Marketplace'
    },
    '/marketplace/v1/refunds/create': {
      payment_id: 'pay_test_123',
      amount: 1000,
      reason: 'requested_by_customer',
      notify_customer: true
    },
    '/marketplace/v1/subscriptions/create': {
      customer_id: 'cust_test_123',
      plan_id: 'plan_monthly_basic',
      payment_method_id: 'pm_test_123',
      trial_period_days: 14
    },
    '/marketplace/v1/transactions/search': {
      customer_id: 'cust_test_123',
      amount_min: 100,
      amount_max: 5000,
      currency: 'USD',
      status: 'completed',
      date_from: '2024-01-01',
      date_to: '2024-12-31',
      limit: 10
    },
    '/marketplace/v1/payment-methods/create': {
      customer_id: 'cust_test_123',
      type: 'card',
      card: {
        number: '4242424242424242',
        exp_month: 12,
        exp_year: 2025,
        cvc: '123',
        cardholder_name: 'Test Customer'
      },
      is_default: true
    },
    '/marketplace/v1/bank-verification/initiate': {
      customer_id: 'cust_test_123',
      account_holder_name: 'John Doe',
      routing_number: '110000000',
      account_number: '000123456789',
      account_type: 'checking',
      verification_method: 'micro_deposits'
    },
    '/marketplace/v1/fx/convert': {
      from_currency: 'USD',
      to_currency: 'EUR',
      amount: 1000,
      rate_type: 'real_time'
    },
    '/marketplace/v1/credit/score': {
      customer_id: 'cust_test_123',
      ssn: '123456789',
      date_of_birth: '1990-01-01',
      address: {
        street: '123 Main St',
        city: 'San Francisco',
        state: 'CA',
        zip_code: '94105'
      },
      annual_income: 75000,
      employment_status: 'employed'
    },
    '/marketplace/v1/financial-reporting/revenue-analytics': {
      date_from: '2024-01-01',
      date_to: '2024-12-31',
      group_by: 'month',
      currency: 'USD',
      include_refunds: true
    }
  }

  return samples[endpoint] || {}
}

const getQueryParameters = (endpoint: string) => {
  const queryParams: Record<string, string[]> = {
    '/marketplace/v1/payments/{payment_id}': ['payment_id=pay_test_123'],
    '/marketplace/v1/refunds/{refund_id}': ['refund_id=ref_test_123'],
    '/marketplace/v1/subscriptions/{subscription_id}': ['subscription_id=sub_test_123'],
    '/marketplace/v1/fx/rates': ['base_currency=USD', 'target_currencies=EUR,GBP,JPY'],
    '/marketplace/v1/bank-verification/routing/{routing_number}/info': ['routing_number=110000000'],
    '/marketplace/v1/transactions/analytics/summary': ['date_from=2024-01-01', 'date_to=2024-12-31', 'currency=USD']
  }

  return queryParams[endpoint] || []
}

export function ApiTestModal({ isOpen, onClose, api, selectedApiKey }: ApiTestModalProps) {
  const [activeTab, setActiveTab] = useState('request')
  const [requestBody, setRequestBody] = useState('')
  const [queryParams, setQueryParams] = useState('')
  const [customHeaders, setCustomHeaders] = useState('')
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [showApiKey, setShowApiKey] = useState(false)
  
  const { toast } = useToast()

  // Initialize form data when modal opens or API changes
  useEffect(() => {
    if (isOpen && api) {
      const sampleBody = getSampleRequestBody(api.endpoint, api.method)
      const sampleParams = getQueryParameters(api.endpoint)
      
      setRequestBody(JSON.stringify(sampleBody, null, 2))
      setQueryParams(sampleParams.join('\n'))
      setCustomHeaders('Content-Type: application/json')
      setTestResult(null)
      setActiveTab('request')
    }
  }, [isOpen, api])

  const executeApiTest = async () => {
    if (!selectedApiKey) {
      toast({
        title: 'API Key Required',
        description: 'Please select an API key to test the API',
        variant: 'destructive'
      })
      return
    }

    console.log('Testing with API key:', selectedApiKey)
    console.log('API endpoint:', api.endpoint)
    console.log('API method:', api.method)

    setIsLoading(true)
    setTestResult(null)

    try {
      const startTime = Date.now()
      
      // Parse query parameters
      const parsedQueryParams: Record<string, string> = {}
      if (queryParams) {
        queryParams.split('\n').forEach(line => {
          const [key, value] = line.split('=').map(s => s.trim())
          if (key && value) {
            parsedQueryParams[key] = value
          }
        })
      }

      // Parse request body
      let body: any = undefined
      if (api.method !== 'GET' && requestBody.trim()) {
        try {
          body = JSON.parse(requestBody)
        } catch (e) {
          throw new Error('Invalid JSON in request body')
        }
      }

      // Use the marketplace proxy to make the API call
      console.log('Making proxied API request to:', api.endpoint)
      
      const proxyResponse = await fetch('/api/marketplace-proxy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint: api.endpoint,
          method: api.method,
          apiKey: selectedApiKey,
          requestBody: body,
          queryParams: parsedQueryParams,
        }),
      })

      const proxyResult = await proxyResponse.json()
      
      const success = proxyResult.success
      const status = proxyResult.status
      const statusText = proxyResult.statusText
      const responseData = proxyResult.data

      const endTime = Date.now()
      const responseTime = proxyResult.responseTime || (endTime - startTime)

      // Use the response headers from the proxy, or build default ones
      const responseHeaders: Record<string, string> = proxyResult.headers || {
        'content-type': 'application/json',
        'x-response-time': `${responseTime}ms`,
        'x-api-key': selectedApiKey.slice(0, 12) + '...',
        'access-control-allow-origin': '*'
      }

      const apiResponse: ApiTestResponse = {
        status,
        statusText,
        data: responseData,
        headers: responseHeaders,
        responseTime,
        timestamp: proxyResult.timestamp || new Date().toISOString()
      }

      setTestResult({
        success,
        response: apiResponse,
        error: null
      })

      setActiveTab('response')

      toast({
        title: success ? 'API Test Successful' : 'API Test Failed',
        description: `${api.method} ${api.endpoint} - ${status} ${statusText}`,
        variant: success ? 'default' : 'destructive'
      })

    } catch (error: any) {
      setTestResult({
        success: false,
        response: null,
        error: error.message || 'An unexpected error occurred'
      })

      setActiveTab('response')

      toast({
        title: 'API Test Error',
        description: error.message || 'Failed to execute API test',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text).then(() => {
      toast({
        title: 'Copied to Clipboard',
        description: `${type} copied to clipboard`
      })
    })
  }

  const downloadResponse = () => {
    if (!testResult?.response) return

    const data = JSON.stringify(testResult.response, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    
    const a = document.createElement('a')
    a.href = url
    a.download = `api-test-${api.endpoint.replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getStatusBadgeColor = (status: number) => {
    if (status >= 200 && status < 300) return 'bg-green-100 text-green-800'
    if (status >= 300 && status < 400) return 'bg-blue-100 text-blue-800'
    if (status >= 400 && status < 500) return 'bg-yellow-100 text-yellow-800'
    return 'bg-red-100 text-red-800'
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <DialogTitle className="flex items-center gap-3">
                <Badge className={`${api.method === 'GET' ? 'bg-blue-100 text-blue-800' : 
                  api.method === 'POST' ? 'bg-green-100 text-green-800' :
                  api.method === 'PUT' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'}`}>
                  {api.method}
                </Badge>
                <span className="font-mono text-lg">{api.endpoint}</span>
              </DialogTitle>
              <DialogDescription className="text-sm">
                {api.description}
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                onClick={executeApiTest}
                disabled={isLoading || !selectedApiKey}
                className="flex items-center gap-2"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                {isLoading ? 'Testing...' : 'Test API'}
              </Button>
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="request">Request</TabsTrigger>
              <TabsTrigger value="response" disabled={!testResult}>
                Response
                {testResult && (
                  <Badge 
                    className={`ml-2 ${testResult.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
                    variant="secondary"
                  >
                    {testResult.response?.status || 'Error'}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="code">Code Examples</TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-auto mt-4">
              <TabsContent value="request" className="space-y-6 mt-0">
                {/* API Key Section */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Authentication</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="api-key">API Key</Label>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowApiKey(!showApiKey)}
                      >
                        {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                    <Input
                      id="api-key"
                      type={showApiKey ? 'text' : 'password'}
                      value={selectedApiKey || 'No API key selected'}
                      readOnly
                      className="font-mono text-sm"
                      placeholder="Select an API key from the marketplace page"
                    />
                    {!selectedApiKey && (
                      <p className="text-xs text-orange-600 mt-1">
                        Please select an API key from the dropdown on the marketplace page to test APIs
                      </p>
                    )}
                  </CardContent>
                </Card>

                {/* Query Parameters */}
                {(api.method === 'GET' || queryParams) && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">Query Parameters</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(queryParams, 'Query parameters')}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <Textarea
                        value={queryParams}
                        onChange={(e) => setQueryParams(e.target.value)}
                        placeholder="key1=value1&#10;key2=value2"
                        className="font-mono text-sm"
                        rows={3}
                      />
                    </CardContent>
                  </Card>
                )}

                {/* Request Body */}
                {api.method !== 'GET' && (
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">Request Body</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(requestBody, 'Request body')}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <Textarea
                        value={requestBody}
                        onChange={(e) => setRequestBody(e.target.value)}
                        placeholder="Enter JSON request body"
                        className="font-mono text-sm"
                        rows={12}
                      />
                    </CardContent>
                  </Card>
                )}

                {/* Custom Headers */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm">Headers</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Textarea
                      value={customHeaders}
                      onChange={(e) => setCustomHeaders(e.target.value)}
                      placeholder="Header-Name: Header-Value"
                      className="font-mono text-sm"
                      rows={3}
                    />
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="response" className="space-y-4 mt-0">
                {testResult ? (
                  <>
                    {/* Response Status */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm">Response Status</CardTitle>
                          <div className="flex items-center gap-2">
                            <Badge className={getStatusBadgeColor(testResult.response?.status || 0)}>
                              {testResult.response?.status} {testResult.response?.statusText}
                            </Badge>
                            {testResult.response && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={downloadResponse}
                              >
                                <Download className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <Label>Response Time</Label>
                            <div className="flex items-center gap-2 mt-1">
                              <Clock className="h-4 w-4 text-muted-foreground" />
                              <span>{testResult.response?.responseTime}ms</span>
                            </div>
                          </div>
                          <div>
                            <Label>Timestamp</Label>
                            <div className="mt-1 text-muted-foreground">
                              {testResult.response?.timestamp && new Date(testResult.response.timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>

                    {/* Response Body */}
                    <Card>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm">Response Body</CardTitle>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyToClipboard(
                              JSON.stringify(testResult.response?.data, null, 2),
                              'Response body'
                            )}
                          >
                            <Copy className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono max-h-96">
                          {testResult.error ? testResult.error : JSON.stringify(testResult.response?.data, null, 2)}
                        </pre>
                      </CardContent>
                    </Card>

                    {/* Response Headers */}
                    {testResult.response?.headers && (
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-sm">Response Headers</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono max-h-32">
                            {JSON.stringify(testResult.response.headers, null, 2)}
                          </pre>
                        </CardContent>
                      </Card>
                    )}
                  </>
                ) : (
                  <Card>
                    <CardContent className="flex items-center justify-center py-12">
                      <div className="text-center space-y-3">
                        <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto" />
                        <div>
                          <p className="font-medium">No Response Yet</p>
                          <p className="text-sm text-muted-foreground">
                            Click "Test API" to execute the request and see the response
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </TabsContent>

              <TabsContent value="code" className="space-y-4 mt-0">
                <div className="grid gap-4">
                  {/* cURL Example */}
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">cURL</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const curlCommand = `curl -X ${api.method} \\
  "${api.endpoint}" \\
  -H "X-API-Key: ${selectedApiKey}" \\
  -H "Content-Type: application/json"${
                              api.method !== 'GET' && requestBody.trim() 
                                ? ` \\\n  -d '${requestBody.replace(/'/g, "\\'")}'`
                                : ''
                            }`
                            copyToClipboard(curlCommand, 'cURL command')
                          }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono">
{`curl -X ${api.method} \\
  "${api.endpoint}" \\
  -H "X-API-Key: ${selectedApiKey}" \\
  -H "Content-Type: application/json"${
  api.method !== 'GET' && requestBody.trim() 
    ? ` \\\n  -d '${requestBody.replace(/'/g, "\\'")}'`
    : ''
}`}
                      </pre>
                    </CardContent>
                  </Card>

                  {/* JavaScript Example */}
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">JavaScript (fetch)</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const jsCode = `const response = await fetch('${api.endpoint}', {
  method: '${api.method}',
  headers: {
    'X-API-Key': '${selectedApiKey}',
    'Content-Type': 'application/json'
  }${api.method !== 'GET' && requestBody.trim() ? `,\n  body: JSON.stringify(${requestBody})` : ''}
});

const data = await response.json();
console.log(data);`
                            copyToClipboard(jsCode, 'JavaScript code')
                          }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono">
{`const response = await fetch('${api.endpoint}', {
  method: '${api.method}',
  headers: {
    'X-API-Key': '${selectedApiKey}',
    'Content-Type': 'application/json'
  }${api.method !== 'GET' && requestBody.trim() ? `,\n  body: JSON.stringify(${requestBody})` : ''}
});

const data = await response.json();
console.log(data);`}
                      </pre>
                    </CardContent>
                  </Card>

                  {/* Python Example */}
                  <Card>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">Python (requests)</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            const pythonCode = `import requests
import json

url = "${api.endpoint}"
headers = {
    "X-API-Key": "${selectedApiKey}",
    "Content-Type": "application/json"
}

${api.method !== 'GET' && requestBody.trim() 
  ? `data = ${requestBody}

response = requests.${api.method.toLowerCase()}(url, headers=headers, json=data)` 
  : `response = requests.${api.method.toLowerCase()}(url, headers=headers)`}
print(response.json())`
                            copyToClipboard(pythonCode, 'Python code')
                          }}
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm font-mono">
{`import requests
import json

url = "${api.endpoint}"
headers = {
    "X-API-Key": "${selectedApiKey}",
    "Content-Type": "application/json"
}

${api.method !== 'GET' && requestBody.trim() 
  ? `data = ${requestBody}

response = requests.${api.method.toLowerCase()}(url, headers=headers, json=data)` 
  : `response = requests.${api.method.toLowerCase()}(url, headers=headers)`}
print(response.json())`}
                      </pre>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}