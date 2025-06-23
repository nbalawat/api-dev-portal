export interface KeyTemplate {
  id: string;
  name: string;
  description: string;
  environment: 'development' | 'staging' | 'production';
  defaultScopes: string[];
  defaultExpirationDays: number;
  rateLimit?: number;
  rateLimitPeriod?: string;
  allowedIps?: string[];
  allowedDomains?: string[];
  icon?: string;
  color?: string;
}

export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
  templates: KeyTemplate[];
}

export const DEFAULT_TEMPLATES: TemplateCategory[] = [
  {
    id: 'environment',
    name: 'Environment Templates',
    description: 'Pre-configured templates for different deployment environments',
    templates: [
      {
        id: 'dev-template',
        name: 'Development',
        description: 'Local development and testing with relaxed limits',
        environment: 'development',
        defaultScopes: ['read', 'write'],
        defaultExpirationDays: 30,
        rateLimit: 1000,
        rateLimitPeriod: 'hour',
        icon: '🛠️',
        color: 'bg-blue-100 text-blue-800'
      },
      {
        id: 'staging-template',
        name: 'Staging',
        description: 'Staging environment with moderate restrictions',
        environment: 'staging',
        defaultScopes: ['read', 'write'],
        defaultExpirationDays: 60,
        rateLimit: 500,
        rateLimitPeriod: 'hour',
        icon: '🧪',
        color: 'bg-yellow-100 text-yellow-800'
      },
      {
        id: 'prod-template',
        name: 'Production',
        description: 'Production environment with strict security',
        environment: 'production',
        defaultScopes: ['read'],
        defaultExpirationDays: 90,
        rateLimit: 100,
        rateLimitPeriod: 'hour',
        icon: '🚀',
        color: 'bg-green-100 text-green-800'
      }
    ]
  },
  {
    id: 'service',
    name: 'Service Templates',
    description: 'Templates optimized for different types of services',
    templates: [
      {
        id: 'web-app-template',
        name: 'Web Application',
        description: 'For web applications and frontend clients',
        environment: 'production',
        defaultScopes: ['read', 'user:profile'],
        defaultExpirationDays: 365,
        rateLimit: 200,
        rateLimitPeriod: 'hour',
        icon: '🌐',
        color: 'bg-purple-100 text-purple-800'
      },
      {
        id: 'mobile-app-template',
        name: 'Mobile Application',
        description: 'For mobile apps with user authentication',
        environment: 'production',
        defaultScopes: ['read', 'write', 'user:profile'],
        defaultExpirationDays: 180,
        rateLimit: 150,
        rateLimitPeriod: 'hour',
        icon: '📱',
        color: 'bg-indigo-100 text-indigo-800'
      },
      {
        id: 'server-template',
        name: 'Server Application',
        description: 'For backend services and server-to-server communication',
        environment: 'production',
        defaultScopes: ['read', 'write', 'admin'],
        defaultExpirationDays: 90,
        rateLimit: 1000,
        rateLimitPeriod: 'hour',
        icon: '🖥️',
        color: 'bg-gray-100 text-gray-800'
      },
      {
        id: 'integration-template',
        name: 'Third-party Integration',
        description: 'For external integrations and webhook endpoints',
        environment: 'production',
        defaultScopes: ['read', 'webhook'],
        defaultExpirationDays: 180,
        rateLimit: 50,
        rateLimitPeriod: 'hour',
        icon: '🔗',
        color: 'bg-teal-100 text-teal-800'
      }
    ]
  },
  {
    id: 'permission',
    name: 'Permission Templates',
    description: 'Templates with specific permission levels',
    templates: [
      {
        id: 'readonly-template',
        name: 'Read Only',
        description: 'Read-only access for monitoring and analytics',
        environment: 'production',
        defaultScopes: ['read'],
        defaultExpirationDays: 180,
        rateLimit: 300,
        rateLimitPeriod: 'hour',
        icon: '👁️',
        color: 'bg-blue-100 text-blue-800'
      },
      {
        id: 'limited-write-template',
        name: 'Limited Write',
        description: 'Read and limited write permissions',
        environment: 'production',
        defaultScopes: ['read', 'write:limited'],
        defaultExpirationDays: 90,
        rateLimit: 100,
        rateLimitPeriod: 'hour',
        icon: '✏️',
        color: 'bg-orange-100 text-orange-800'
      },
      {
        id: 'admin-template',
        name: 'Administrative',
        description: 'Full administrative access (use with caution)',
        environment: 'production',
        defaultScopes: ['read', 'write', 'admin', 'user:manage'],
        defaultExpirationDays: 30,
        rateLimit: 50,
        rateLimitPeriod: 'hour',
        icon: '🔐',
        color: 'bg-red-100 text-red-800'
      }
    ]
  }
];

export interface CreateKeyFromTemplateData {
  templateId: string;
  name: string;
  description?: string;
  customScopes?: string[];
  customExpirationDays?: number;
  customRateLimit?: number;
  customAllowedIps?: string[];
  customAllowedDomains?: string[];
}