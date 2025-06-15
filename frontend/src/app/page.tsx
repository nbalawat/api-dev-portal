'use client'

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-2xl mx-auto text-center p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to API Developer Portal
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Enterprise-grade API management with authentication, analytics, and comprehensive documentation.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-12">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-2">🔑 API Key Management</h3>
            <p className="text-gray-600">Generate, manage, and monitor your API keys with advanced permissions and rate limiting.</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-2">📊 Analytics Dashboard</h3>
            <p className="text-gray-600">Real-time insights into API usage, performance metrics, and detailed reporting.</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-2">👥 User Management</h3>
            <p className="text-gray-600">Role-based access control with admin, developer, and viewer permissions.</p>
          </div>
          
          <div className="bg-white rounded-lg shadow-md p-6">
            <h3 className="text-lg font-semibold mb-2">🛡️ Security First</h3>
            <p className="text-gray-600">Enterprise security with JWT authentication, rate limiting, and audit logging.</p>
          </div>
        </div>

        <div className="mt-12 space-x-4">
          <a 
            href="/dashboard" 
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors"
          >
            Go to Dashboard
          </a>
          <a 
            href="/api/docs" 
            className="inline-block bg-gray-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-gray-700 transition-colors"
          >
            View API Docs
          </a>
        </div>

        <div className="mt-8 text-sm text-gray-500">
          <p>Frontend: Ready | Backend: <span className="text-green-600">Connected</span></p>
        </div>
      </div>
    </div>
  )
}