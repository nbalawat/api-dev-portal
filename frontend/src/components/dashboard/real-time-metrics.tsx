'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
// import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Activity, TrendingUp, TrendingDown, Zap, Shield, Clock, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface SystemMetrics {
  timestamp: string;
  totalRequests: number;
  requestsPerSecond: number;
  averageResponseTime: number;
  errorRate: number;
  activeKeys: number;
  rateLimitHits: number;
  systemHealth: 'healthy' | 'warning' | 'critical';
}

interface RateLimitMetrics {
  ruleName: string;
  scope: string;
  tokensRemaining: number;
  capacity: number;
  utilizationPercent: number;
  successRate: number;
  totalRequests: number;
  rejectedRequests: number;
}

interface BackgroundTaskStatus {
  taskName: string;
  frequency: string;
  enabled: boolean;
  lastRun?: string;
  nextRun?: string;
  runCount: number;
  errorCount: number;
  status: 'running' | 'scheduled' | 'completed' | 'failed';
}

interface AlertItem {
  id: string;
  type: 'info' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

interface RealTimeMetricsProps {
  refreshInterval?: number;
  onRefresh?: () => void;
}

// Mock data generators for demonstration
const generateSystemMetrics = (): SystemMetrics[] => {
  const now = new Date();
  return Array.from({ length: 20 }, (_, i) => ({
    timestamp: new Date(now.getTime() - (19 - i) * 30000).toISOString(),
    totalRequests: Math.floor(Math.random() * 1000) + 500,
    requestsPerSecond: Math.floor(Math.random() * 50) + 10,
    averageResponseTime: Math.floor(Math.random() * 200) + 50,
    errorRate: Math.random() * 5,
    activeKeys: Math.floor(Math.random() * 10) + 45,
    rateLimitHits: Math.floor(Math.random() * 20),
    systemHealth: Math.random() > 0.8 ? 'warning' : 'healthy' as 'healthy' | 'warning' | 'critical'
  }));
};

const generateRateLimitMetrics = (): RateLimitMetrics[] => [
  {
    ruleName: 'global_requests',
    scope: 'global',
    tokensRemaining: 850,
    capacity: 1000,
    utilizationPercent: 15,
    successRate: 98.5,
    totalRequests: 2456,
    rejectedRequests: 38
  },
  {
    ruleName: 'user_requests',
    scope: 'user',
    tokensRemaining: 75,
    capacity: 100,
    utilizationPercent: 25,
    successRate: 95.2,
    totalRequests: 1245,
    rejectedRequests: 63
  },
  {
    ruleName: 'api_key_requests',
    scope: 'api_key',
    tokensRemaining: 40,
    capacity: 50,
    utilizationPercent: 20,
    successRate: 96.8,
    totalRequests: 892,
    rejectedRequests: 29
  },
  {
    ruleName: 'ip_requests',
    scope: 'ip',
    tokensRemaining: 180,
    capacity: 200,
    utilizationPercent: 10,
    successRate: 99.1,
    totalRequests: 1567,
    rejectedRequests: 14
  }
];

const generateBackgroundTasks = (): BackgroundTaskStatus[] => [
  {
    taskName: 'api_key_expiration_check',
    frequency: 'daily',
    enabled: true,
    lastRun: new Date(Date.now() - 3600000).toISOString(),
    nextRun: new Date(Date.now() + 82800000).toISOString(),
    runCount: 15,
    errorCount: 0,
    status: 'completed'
  },
  {
    taskName: 'usage_analytics_aggregation',
    frequency: 'hourly',
    enabled: true,
    lastRun: new Date(Date.now() - 600000).toISOString(),
    nextRun: new Date(Date.now() + 3000000).toISOString(),
    runCount: 156,
    errorCount: 2,
    status: 'scheduled'
  },
  {
    taskName: 'audit_log_cleanup',
    frequency: 'weekly',
    enabled: true,
    lastRun: new Date(Date.now() - 86400000 * 3).toISOString(),
    nextRun: new Date(Date.now() + 86400000 * 4).toISOString(),
    runCount: 8,
    errorCount: 0,
    status: 'scheduled'
  }
];

const generateAlerts = (): AlertItem[] => [
  {
    id: '1',
    type: 'warning',
    title: 'High Rate Limit Usage',
    message: 'User rate limit rule is at 85% capacity',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    acknowledged: false
  },
  {
    id: '2',
    type: 'info',
    title: 'Background Task Completed',
    message: 'API key expiration check completed successfully',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    acknowledged: true
  },
  {
    id: '3',
    type: 'error',
    title: 'Email Notification Failed',
    message: 'Failed to send expiration warning to user@example.com',
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    acknowledged: false
  }
];

const COLORS = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#6366f1'
};

export function RealTimeMetrics({ refreshInterval = 30000, onRefresh }: RealTimeMetricsProps) {
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics[]>(generateSystemMetrics());
  const [rateLimitMetrics, setRateLimitMetrics] = useState<RateLimitMetrics[]>(generateRateLimitMetrics());
  const [backgroundTasks, setBackgroundTasks] = useState<BackgroundTaskStatus[]>(generateBackgroundTasks());
  const [alerts, setAlerts] = useState<AlertItem[]>(generateAlerts());
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  const refreshMetrics = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // In a real app, these would be API calls
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API delay
      setSystemMetrics(generateSystemMetrics());
      setRateLimitMetrics(generateRateLimitMetrics());
      setBackgroundTasks(generateBackgroundTasks());
      setLastUpdated(new Date());
      onRefresh?.();
    } finally {
      setIsRefreshing(false);
    }
  }, [onRefresh]);

  useEffect(() => {
    const interval = setInterval(refreshMetrics, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshMetrics, refreshInterval]);

  const acknowledgeAlert = (alertId: string) => {
    setAlerts(alerts.map(alert => 
      alert.id === alertId ? { ...alert, acknowledged: true } : alert
    ));
  };

  const getHealthIcon = (health: string) => {
    switch (health) {
      case 'healthy': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'warning': return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'critical': return <XCircle className="h-5 w-5 text-red-600" />;
      default: return <CheckCircle className="h-5 w-5 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      'running': 'default',
      'completed': 'secondary',
      'scheduled': 'outline',
      'failed': 'destructive'
    } as const;
    
    return <Badge variant={variants[status as keyof typeof variants] || 'outline'}>{status}</Badge>;
  };

  const latestMetrics = systemMetrics[systemMetrics.length - 1];
  const unacknowledgedAlerts = alerts.filter(alert => !alert.acknowledged);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Real-time System Monitoring</h2>
          <p className="text-gray-600 mt-1">
            Live metrics and system health • Last updated: {lastUpdated.toLocaleTimeString()}
          </p>
        </div>
        <Button onClick={refreshMetrics} disabled={isRefreshing} variant="outline">
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            {getHealthIcon(latestMetrics?.systemHealth)}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{latestMetrics?.systemHealth}</div>
            <p className="text-xs text-muted-foreground">
              {latestMetrics?.activeKeys} active keys
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Requests/Second</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latestMetrics?.requestsPerSecond}</div>
            <p className="text-xs text-muted-foreground">
              {latestMetrics?.totalRequests} total requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latestMetrics?.averageResponseTime}ms</div>
            <p className="text-xs text-muted-foreground">
              {latestMetrics?.errorRate.toFixed(1)}% error rate
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Rate Limit Hits</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{latestMetrics?.rateLimitHits}</div>
            <p className="text-xs text-muted-foreground">
              Last 30 seconds
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alerts */}
      {unacknowledgedAlerts.length > 0 && (
        <Card className="border-yellow-600 bg-yellow-900/20">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <span>Active Alerts ({unacknowledgedAlerts.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {unacknowledgedAlerts.slice(0, 3).map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-3 bg-card rounded border border-border">
                  <div className="flex items-center space-x-3">
                    <Badge variant={alert.type === 'error' ? 'destructive' : alert.type === 'warning' ? 'secondary' : 'default'}>
                      {alert.type}
                    </Badge>
                    <div>
                      <div className="font-medium text-foreground">{alert.title}</div>
                      <div className="text-sm text-muted-foreground">{alert.message}</div>
                    </div>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => acknowledgeAlert(alert.id)}>
                    Acknowledge
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="metrics" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="metrics">System Metrics</TabsTrigger>
          <TabsTrigger value="rate-limits">Rate Limiting</TabsTrigger>
          <TabsTrigger value="background">Background Tasks</TabsTrigger>
          <TabsTrigger value="alerts">Alerts & Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="metrics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle>Request Rate</CardTitle>
                <CardDescription>Requests per second over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={systemMetrics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleTimeString()} />
                    <YAxis />
                    <Tooltip labelFormatter={(value) => new Date(value).toLocaleTimeString()} />
                    <Area type="monotone" dataKey="requestsPerSecond" stroke={COLORS.primary} fill={COLORS.primary} fillOpacity={0.3} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Response Time & Error Rate</CardTitle>
                <CardDescription>Performance metrics over time</CardDescription>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={systemMetrics}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" tickFormatter={(value) => new Date(value).toLocaleTimeString()} />
                    <YAxis yAxisId="left" />
                    <YAxis yAxisId="right" orientation="right" />
                    <Tooltip labelFormatter={(value) => new Date(value).toLocaleTimeString()} />
                    <Line yAxisId="left" type="monotone" dataKey="averageResponseTime" stroke={COLORS.success} name="Response Time (ms)" />
                    <Line yAxisId="right" type="monotone" dataKey="errorRate" stroke={COLORS.error} name="Error Rate (%)" />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="rate-limits" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rateLimitMetrics.map((metric) => (
              <Card key={metric.ruleName}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{metric.ruleName}</span>
                    <Badge variant="outline">{metric.scope}</Badge>
                  </CardTitle>
                  <CardDescription>
                    {metric.totalRequests} total requests • {metric.rejectedRequests} rejected
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Token Usage</span>
                      <span>{metric.tokensRemaining}/{metric.capacity}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-600 h-2 rounded-full transition-all" 
                        style={{ width: `${((metric.capacity - metric.tokensRemaining) / metric.capacity) * 100}%` }}
                      ></div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-gray-600">Success Rate</div>
                      <div className="font-medium text-lg">{metric.successRate.toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Utilization</div>
                      <div className="font-medium text-lg">{metric.utilizationPercent}%</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="background" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Background Task Status</CardTitle>
              <CardDescription>Automated system tasks and their current status</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {backgroundTasks.map((task) => (
                  <div key={task.taskName} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div>
                        <div className="font-medium">{task.taskName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                        <div className="text-sm text-gray-600">
                          Runs {task.frequency} • {task.runCount} executions • {task.errorCount} errors
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-4">
                      <div className="text-right text-sm">
                        {task.lastRun && (
                          <div className="text-gray-600">
                            Last: {new Date(task.lastRun).toLocaleString()}
                          </div>
                        )}
                        {task.nextRun && (
                          <div className="text-gray-600">
                            Next: {new Date(task.nextRun).toLocaleString()}
                          </div>
                        )}
                      </div>
                      {getStatusBadge(task.status)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Alerts & Activity Log</CardTitle>
              <CardDescription>Recent system events and notifications</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`flex items-center justify-between p-3 rounded border border-border ${
                      alert.acknowledged ? 'bg-secondary/50 opacity-75' : 'bg-card'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Badge variant={alert.type === 'error' ? 'destructive' : alert.type === 'warning' ? 'secondary' : 'default'}>
                        {alert.type}
                      </Badge>
                      <div>
                        <div className="font-medium text-foreground">{alert.title}</div>
                        <div className="text-sm text-muted-foreground">{alert.message}</div>
                        <div className="text-xs text-muted-foreground">{new Date(alert.timestamp).toLocaleString()}</div>
                      </div>
                    </div>
                    
                    {!alert.acknowledged && (
                      <Button size="sm" variant="outline" onClick={() => acknowledgeAlert(alert.id)}>
                        Acknowledge
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}