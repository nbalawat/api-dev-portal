import { NextRequest, NextResponse } from 'next/server'

// Use internal backend URL for server-side requests in Docker
// When running in Docker, the frontend container needs to connect to backend container using the service name
const BACKEND_URL = process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  let body: any
  
  try {
    // Get the request body and headers
    body = await request.json()
    const { endpoint, method, apiKey, requestBody, queryParams } = body

    // Build the full URL with path parameter substitution
    let processedEndpoint = endpoint
    const remainingQueryParams: Record<string, string> = {}
    
    // Handle path parameter substitution
    if (queryParams) {
      Object.entries(queryParams).forEach(([key, value]) => {
        const pathParamPattern = `{${key}}`
        if (processedEndpoint.includes(pathParamPattern)) {
          // Replace path parameter in the endpoint
          processedEndpoint = processedEndpoint.replace(pathParamPattern, String(value))
        } else {
          // Keep as query parameter
          remainingQueryParams[key] = String(value)
        }
      })
    }
    
    let url = `${BACKEND_URL}${processedEndpoint}`
    
    // Add remaining query parameters
    if (Object.keys(remainingQueryParams).length > 0) {
      const params = new URLSearchParams()
      Object.entries(remainingQueryParams).forEach(([key, value]) => {
        if (value) params.append(key, value)
      })
      if (params.toString()) {
        url += `?${params.toString()}`
      }
    }

    console.log('Proxying request to:', url)
    console.log('Method:', method)
    console.log('API Key:', apiKey ? `${apiKey.slice(0, 12)}...` : 'none')
    console.log('Backend URL:', BACKEND_URL)

    // Make the request to the backend
    const fetchOptions: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey,
      },
    }

    // Add body for non-GET requests
    if (method !== 'GET' && requestBody) {
      fetchOptions.body = JSON.stringify(requestBody)
    }

    const startTime = Date.now()
    const response = await fetch(url, fetchOptions)
    const endTime = Date.now()

    // Get response data
    let responseData
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('application/json')) {
      responseData = await response.json()
    } else {
      responseData = await response.text()
    }

    // Build response headers object
    const responseHeaders: Record<string, string> = {}
    response.headers.forEach((value, key) => {
      responseHeaders[key] = value
    })

    // Return the proxied response
    return NextResponse.json({
      success: response.ok,
      status: response.status,
      statusText: response.statusText,
      data: responseData,
      headers: responseHeaders,
      responseTime: endTime - startTime,
      timestamp: new Date().toISOString(),
    })

  } catch (error: any) {
    console.error('Marketplace proxy error:', error)
    console.error('Error details:', {
      message: error.message,
      cause: error.cause,
      stack: error.stack,
      backendUrl: BACKEND_URL,
      requestedEndpoint: body?.endpoint,
      method: body?.method
    })
    
    // Provide more detailed error information
    let errorMessage = error.message || 'Unknown error occurred'
    let errorDetails = error.toString()
    
    // Check for common Docker networking issues
    if (error.cause?.code === 'ECONNREFUSED' || error.message.includes('ECONNREFUSED')) {
      errorMessage = 'Connection refused - Backend service may not be running or accessible'
      errorDetails = `Unable to connect to backend at ${BACKEND_URL}. When running in Docker, ensure the backend service is running and accessible.`
    } else if (error.cause?.code === 'ENOTFOUND' || error.message.includes('ENOTFOUND')) {
      errorMessage = 'Backend service not found'
      errorDetails = `Unable to resolve backend host. Check Docker networking configuration.`
    }
    
    return NextResponse.json({
      success: false,
      status: 500,
      statusText: 'Proxy Error',
      data: {
        error: errorMessage,
        details: errorDetails,
        type: 'marketplace_proxy_error',
        backendUrl: BACKEND_URL,
        debug: {
          endpoint: body?.endpoint,
          method: body?.method,
          errorCode: error.cause?.code
        }
      },
      headers: {},
      responseTime: 0,
      timestamp: new Date().toISOString(),
    })
  }
}