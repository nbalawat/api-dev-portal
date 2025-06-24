'use client';

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
// import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { CheckCircle, XCircle, AlertTriangle, Trash2, RotateCcw, Power, PowerOff, Download, Filter, X } from 'lucide-react';

interface APIKey {
  id: string;
  name: string;
  keyId: string;
  status: 'active' | 'inactive' | 'revoked' | 'expired';
  environment: string;
  createdAt: string;
  expiresAt?: string;
  lastUsed?: string;
  requestCount: number;
}

interface BulkOperation {
  type: 'enable' | 'disable' | 'revoke' | 'rotate' | 'delete' | 'export';
  label: string;
  icon: React.ReactNode;
  description: string;
  variant: 'default' | 'destructive' | 'secondary';
  requiresConfirmation: boolean;
  requiresReason?: boolean;
}

interface BulkOperationResult {
  keyId: string;
  success: boolean;
  error?: string;
}

interface BulkOperationsProps {
  apiKeys: APIKey[];
  onBulkOperation: (operation: string, keyIds: string[], reason?: string) => Promise<BulkOperationResult[]>;
  isLoading?: boolean;
}

const BULK_OPERATIONS: BulkOperation[] = [
  {
    type: 'enable',
    label: 'Enable Keys',
    icon: <Power className="h-4 w-4" />,
    description: 'Activate selected API keys',
    variant: 'default',
    requiresConfirmation: false,
  },
  {
    type: 'disable',
    label: 'Disable Keys',
    icon: <PowerOff className="h-4 w-4" />,
    description: 'Temporarily disable selected API keys',
    variant: 'secondary',
    requiresConfirmation: true,
    requiresReason: true,
  },
  {
    type: 'rotate',
    label: 'Rotate Keys',
    icon: <RotateCcw className="h-4 w-4" />,
    description: 'Generate new secrets for selected keys',
    variant: 'default',
    requiresConfirmation: true,
    requiresReason: true,
  },
  {
    type: 'revoke',
    label: 'Revoke Keys',
    icon: <XCircle className="h-4 w-4" />,
    description: 'Permanently revoke selected API keys',
    variant: 'destructive',
    requiresConfirmation: true,
    requiresReason: true,
  },
  {
    type: 'delete',
    label: 'Delete Keys',
    icon: <Trash2 className="h-4 w-4" />,
    description: 'Permanently delete selected API keys and all data',
    variant: 'destructive',
    requiresConfirmation: true,
    requiresReason: true,
  },
  {
    type: 'export',
    label: 'Export Data',
    icon: <Download className="h-4 w-4" />,
    description: 'Export usage data for selected keys',
    variant: 'secondary',
    requiresConfirmation: false,
  },
];

export function BulkOperations({ apiKeys, onBulkOperation, isLoading }: BulkOperationsProps) {
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterEnvironment, setFilterEnvironment] = useState<string>('all');
  const [showResults, setShowResults] = useState(false);
  const [operationResults, setOperationResults] = useState<BulkOperationResult[]>([]);
  const [operationProgress, setOperationProgress] = useState(0);
  const [currentOperation, setCurrentOperation] = useState<string>('');

  // Filter keys based on selected filters
  const filteredKeys = apiKeys.filter(key => {
    if (filterStatus !== 'all' && key.status !== filterStatus) return false;
    if (filterEnvironment !== 'all' && key.environment !== filterEnvironment) return false;
    return true;
  });

  // Get unique environments
  const environments = Array.from(new Set(apiKeys.map(key => key.environment)));

  const handleSelectAll = useCallback(() => {
    if (selectedKeys.size === filteredKeys.length) {
      setSelectedKeys(new Set());
    } else {
      setSelectedKeys(new Set(filteredKeys.map(key => key.id)));
    }
  }, [filteredKeys, selectedKeys.size]);

  const handleSelectKey = useCallback((keyId: string) => {
    const newSelected = new Set(selectedKeys);
    if (newSelected.has(keyId)) {
      newSelected.delete(keyId);
    } else {
      newSelected.add(keyId);
    }
    setSelectedKeys(newSelected);
  }, [selectedKeys]);

  const handleBulkOperation = async (operation: BulkOperation, reason?: string) => {
    if (selectedKeys.size === 0) return;

    setCurrentOperation(operation.label);
    setOperationProgress(0);
    setShowResults(false);

    try {
      const keyIds = Array.from(selectedKeys);
      const results = await onBulkOperation(operation.type, keyIds, reason);
      
      setOperationResults(results);
      setShowResults(true);
      setOperationProgress(100);
      
      // Clear selection after successful operation
      setSelectedKeys(new Set());
    } catch (error) {
      console.error('Bulk operation failed:', error);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active': return 'default';
      case 'inactive': return 'secondary';
      case 'revoked': return 'destructive';
      case 'expired': return 'outline';
      default: return 'secondary';
    }
  };

  const getKeyEnvironment = (keyName: string) => {
    const name = keyName.toLowerCase();
    if (name.includes('prod')) return 'production';
    if (name.includes('dev')) return 'development';
    if (name.includes('staging') || name.includes('test')) return 'staging';
    return 'production'; // default
  };

  const getDisplayName = (key: any) => {
    if (key.name && key.name.trim() && key.name !== key.key_id && key.name !== key.id) {
      return key.name;
    }
    // Try to extract from key_id pattern like "ANALYTICS_TEST_KEY"
    if (key.key_id && key.key_id.includes('_')) {
      const parts = key.key_id.split('_');
      if (parts.length > 1 && !parts[0].startsWith('ak_')) {
        return parts.join(' ').replace(/([A-Z])/g, ' $1').trim();
      }
    }
    // Fallback to a short readable format
    return `API Key ${key.key_id?.slice(-8) || key.id?.slice(-8) || 'Unknown'}`;
  };

  const BulkOperationDialog = ({ operation }: { operation: BulkOperation }) => {
    const [reason, setReason] = useState('');
    
    return (
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant={operation.variant}
            size="sm"
            disabled={selectedKeys.size === 0 || isLoading}
            className="flex items-center space-x-2"
          >
            {operation.icon}
            <span>{operation.label}</span>
            <Badge variant="secondary" className="ml-2">
              {selectedKeys.size}
            </Badge>
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center space-x-2">
              {operation.icon}
              <span>{operation.label}</span>
            </AlertDialogTitle>
            <AlertDialogDescription>
              {operation.description}
              <br />
              <strong>This will affect {selectedKeys.size} API key(s).</strong>
            </AlertDialogDescription>
          </AlertDialogHeader>
          
          {operation.requiresReason && (
            <div className="space-y-2">
              <Label htmlFor="reason">Reason for this action *</Label>
              <Textarea
                id="reason"
                placeholder="Please provide a reason for this bulk operation..."
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
          )}

          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => handleBulkOperation(operation, reason)}
              disabled={operation.requiresReason && !reason.trim()}
              className={operation.variant === 'destructive' ? 'bg-red-600 hover:bg-red-700' : ''}
            >
              Confirm {operation.label}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    );
  };

  const ResultsDialog = () => (
    <Card className={`${showResults ? 'block' : 'hidden'} mb-6`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span>Operation Complete: {currentOperation}</span>
            </CardTitle>
            <CardDescription>
              Processed {operationResults.length} API keys
            </CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setShowResults(false)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
          <div 
            className="bg-blue-600 h-2 rounded-full transition-all" 
            style={{ width: `${operationProgress}%` }}
          ></div>
        </div>
        
        <div className="space-y-2 max-h-60 overflow-y-auto">
          {operationResults.map((result) => {
            const key = apiKeys.find(k => k.id === result.keyId);
            return (
              <div key={result.keyId} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <span className="font-medium">{key?.name || result.keyId}</span>
                <div className="flex items-center space-x-2">
                  {result.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <span className={`text-sm ${result.success ? 'text-green-600' : 'text-red-600'}`}>
                    {result.success ? 'Success' : result.error}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Bulk Operations</h2>
        <p className="text-muted-foreground mt-1">
          Select multiple API keys to perform batch operations efficiently.
        </p>
      </div>

      <ResultsDialog />

      {/* Filters and Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Filter className="h-5 w-5" />
            <span>Filter & Select</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center space-x-2">
              <Label htmlFor="status-filter">Status:</Label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                  <SelectItem value="revoked">Revoked</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center space-x-2">
              <Label htmlFor="env-filter">Environment:</Label>
              <Select value={filterEnvironment} onValueChange={setFilterEnvironment}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="All environments" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All environments</SelectItem>
                  {environments.map(env => (
                    <SelectItem key={env} value={env}>{env}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="select-all"
                checked={selectedKeys.size === filteredKeys.length && filteredKeys.length > 0}
                onCheckedChange={handleSelectAll}
              />
              <Label htmlFor="select-all">
                Select all ({filteredKeys.length} keys)
              </Label>
            </div>
            
            {selectedKeys.size > 0 && (
              <Badge variant="secondary">
                {selectedKeys.size} selected
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Bulk Actions</CardTitle>
          <CardDescription>
            Perform operations on {selectedKeys.size} selected key(s)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {BULK_OPERATIONS.map((operation) => (
              <BulkOperationDialog key={operation.type} operation={operation} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Key List */}
      <Card>
        <CardHeader>
          <CardTitle>API Keys ({filteredKeys.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredKeys.map((key) => (
              <div
                key={key.id}
                className={`flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 transition-colors ${
                  selectedKeys.has(key.id) ? 'bg-blue-50 border-blue-200' : ''
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Checkbox
                    checked={selectedKeys.has(key.id)}
                    onCheckedChange={() => handleSelectKey(key.id)}
                  />
                  <div>
                    <div className="font-medium text-foreground">{getDisplayName(key)}</div>
                    <div className="text-sm text-muted-foreground">
                      {key.key_id || key.key} • Created {new Date(key.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Badge variant={getStatusBadgeVariant(key.status)}>
                    {key.status}
                  </Badge>
                  <Badge variant="outline">
                    {getKeyEnvironment(key.name)}
                  </Badge>
                  <span className="text-sm text-muted-foreground">
                    {key.total_requests || key.request_count || 0} requests
                  </span>
                </div>
              </div>
            ))}
            
            {filteredKeys.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No API keys match the current filters.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}