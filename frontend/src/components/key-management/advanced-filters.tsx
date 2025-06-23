'use client';

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { Separator } from '@/components/ui/separator';
import { Search, Filter, X, Calendar as CalendarIcon, SlidersHorizontal, Save, Bookmark } from 'lucide-react';
import { format } from 'date-fns';

export interface FilterCriteria {
  search?: string;
  status?: string[];
  environment?: string[];
  scopes?: string[];
  createdAfter?: Date;
  createdBefore?: Date;
  expiresAfter?: Date;
  expiresBefore?: Date;
  lastUsedAfter?: Date;
  lastUsedBefore?: Date;
  minRequests?: number;
  maxRequests?: number;
  hasExpiration?: boolean;
  hasIpRestriction?: boolean;
  hasDomainRestriction?: boolean;
}

export interface SavedFilter {
  id: string;
  name: string;
  description?: string;
  criteria: FilterCriteria;
  isDefault?: boolean;
}

interface AdvancedFiltersProps {
  filters: FilterCriteria;
  onFiltersChange: (filters: FilterCriteria) => void;
  savedFilters?: SavedFilter[];
  onSaveFilter?: (name: string, description?: string) => void;
  onLoadFilter?: (filter: SavedFilter) => void;
  onDeleteFilter?: (filterId: string) => void;
  availableScopes?: string[];
  availableEnvironments?: string[];
  totalKeys?: number;
  filteredKeys?: number;
}

const DEFAULT_SAVED_FILTERS: SavedFilter[] = [
  {
    id: 'active-prod',
    name: 'Active Production Keys',
    description: 'All active keys in production environment',
    criteria: {
      status: ['active'],
      environment: ['production']
    }
  },
  {
    id: 'expiring-soon',
    name: 'Expiring Soon',
    description: 'Keys expiring in the next 30 days',
    criteria: {
      status: ['active'],
      expiresBefore: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
    }
  },
  {
    id: 'unused-keys',
    name: 'Unused Keys',
    description: 'Keys that have never been used',
    criteria: {
      maxRequests: 0
    }
  },
  {
    id: 'high-usage',
    name: 'High Usage Keys',
    description: 'Keys with more than 1000 requests',
    criteria: {
      minRequests: 1000
    }
  }
];

export function AdvancedFilters({
  filters,
  onFiltersChange,
  savedFilters = DEFAULT_SAVED_FILTERS,
  onSaveFilter,
  onLoadFilter,
  onDeleteFilter,
  availableScopes = ['read', 'write', 'admin', 'user:profile', 'user:manage', 'webhook', 'analytics'],
  availableEnvironments = ['development', 'staging', 'production'],
  totalKeys = 0,
  filteredKeys = 0
}: AdvancedFiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [saveFilterName, setSaveFilterName] = useState('');
  const [saveFilterDescription, setSaveFilterDescription] = useState('');
  const [showSaveDialog, setShowSaveDialog] = useState(false);

  const updateFilter = useCallback((key: keyof FilterCriteria, value: any) => {
    onFiltersChange({
      ...filters,
      [key]: value
    });
  }, [filters, onFiltersChange]);

  const clearAllFilters = () => {
    onFiltersChange({});
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (filters.search) count++;
    if (filters.status?.length) count++;
    if (filters.environment?.length) count++;
    if (filters.scopes?.length) count++;
    if (filters.createdAfter || filters.createdBefore) count++;
    if (filters.expiresAfter || filters.expiresBefore) count++;
    if (filters.lastUsedAfter || filters.lastUsedBefore) count++;
    if (filters.minRequests !== undefined || filters.maxRequests !== undefined) count++;
    if (filters.hasExpiration !== undefined) count++;
    if (filters.hasIpRestriction !== undefined) count++;
    if (filters.hasDomainRestriction !== undefined) count++;
    return count;
  };

  const handleArrayFilter = (key: keyof FilterCriteria, value: string, currentArray?: string[]) => {
    const current = currentArray || [];
    const newArray = current.includes(value)
      ? current.filter(item => item !== value)
      : [...current, value];
    updateFilter(key, newArray.length > 0 ? newArray : undefined);
  };

  const handleSaveFilter = () => {
    if (onSaveFilter && saveFilterName.trim()) {
      onSaveFilter(saveFilterName.trim(), saveFilterDescription.trim() || undefined);
      setSaveFilterName('');
      setSaveFilterDescription('');
      setShowSaveDialog(false);
    }
  };

  const DateRangePicker = ({ 
    label, 
    afterDate, 
    beforeDate, 
    onAfterChange, 
    onBeforeChange 
  }: {
    label: string;
    afterDate?: Date;
    beforeDate?: Date;
    onAfterChange: (date?: Date) => void;
    onBeforeChange: (date?: Date) => void;
  }) => (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex space-x-2">
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="flex-1">
              <CalendarIcon className="h-4 w-4 mr-2" />
              {afterDate ? format(afterDate, 'MMM dd, yyyy') : 'After...'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0">
            <Calendar
              mode="single"
              selected={afterDate}
              onSelect={onAfterChange}
              initialFocus
            />
          </PopoverContent>
        </Popover>
        
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="flex-1">
              <CalendarIcon className="h-4 w-4 mr-2" />
              {beforeDate ? format(beforeDate, 'MMM dd, yyyy') : 'Before...'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0">
            <Calendar
              mode="single"
              selected={beforeDate}
              onSelect={onBeforeChange}
              initialFocus
            />
          </PopoverContent>
        </Popover>
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {/* Quick Search and Basic Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <Search className="h-5 w-5" />
              <span>Search & Filter</span>
            </CardTitle>
            <div className="flex items-center space-x-2">
              <Badge variant="secondary">
                {filteredKeys} of {totalKeys} keys
              </Badge>
              {getActiveFilterCount() > 0 && (
                <Button variant="outline" size="sm" onClick={clearAllFilters}>
                  <X className="h-4 w-4 mr-1" />
                  Clear ({getActiveFilterCount()})
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input
              placeholder="Search by name, description, or key ID..."
              value={filters.search || ''}
              onChange={(e) => updateFilter('search', e.target.value || undefined)}
              className="pl-10"
            />
          </div>

          {/* Quick Filters */}
          <div className="flex flex-wrap gap-2">
            <div className="flex items-center space-x-2">
              <Label>Status:</Label>
              {['active', 'inactive', 'revoked', 'expired'].map((status) => (
                <Badge
                  key={status}
                  variant={filters.status?.includes(status) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => handleArrayFilter('status', status, filters.status)}
                >
                  {status}
                </Badge>
              ))}
            </div>
            
            <Separator orientation="vertical" className="h-6" />
            
            <div className="flex items-center space-x-2">
              <Label>Environment:</Label>
              {availableEnvironments.map((env) => (
                <Badge
                  key={env}
                  variant={filters.environment?.includes(env) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => handleArrayFilter('environment', env, filters.environment)}
                >
                  {env}
                </Badge>
              ))}
            </div>
          </div>

          {/* Advanced Filters Toggle */}
          <div className="flex items-center justify-between pt-2 border-t">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center space-x-2"
            >
              <SlidersHorizontal className="h-4 w-4" />
              <span>Advanced Filters</span>
              {getActiveFilterCount() > 2 && (
                <Badge variant="secondary" className="ml-2">
                  {getActiveFilterCount() - 2}+ active
                </Badge>
              )}
            </Button>

            <div className="flex items-center space-x-2">
              {/* Saved Filters */}
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Bookmark className="h-4 w-4 mr-2" />
                    Saved Filters
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80">
                  <div className="space-y-2">
                    <h4 className="font-medium">Saved Filters</h4>
                    {savedFilters.map((savedFilter) => (
                      <div key={savedFilter.id} className="flex items-center justify-between p-2 hover:bg-gray-50 rounded">
                        <div
                          className="flex-1 cursor-pointer"
                          onClick={() => onLoadFilter?.(savedFilter)}
                        >
                          <div className="font-medium text-sm">{savedFilter.name}</div>
                          {savedFilter.description && (
                            <div className="text-xs text-gray-600">{savedFilter.description}</div>
                          )}
                        </div>
                        {onDeleteFilter && !savedFilter.isDefault && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => onDeleteFilter(savedFilter.id)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    ))}
                  </div>
                </PopoverContent>
              </Popover>

              {/* Save Current Filter */}
              {onSaveFilter && getActiveFilterCount() > 0 && (
                <Popover open={showSaveDialog} onOpenChange={setShowSaveDialog}>
                  <PopoverTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Save className="h-4 w-4 mr-2" />
                      Save Filter
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-80">
                    <div className="space-y-3">
                      <h4 className="font-medium">Save Current Filter</h4>
                      <div>
                        <Label htmlFor="filter-name">Filter Name</Label>
                        <Input
                          id="filter-name"
                          placeholder="e.g., My Custom Filter"
                          value={saveFilterName}
                          onChange={(e) => setSaveFilterName(e.target.value)}
                        />
                      </div>
                      <div>
                        <Label htmlFor="filter-description">Description (optional)</Label>
                        <Input
                          id="filter-description"
                          placeholder="Brief description..."
                          value={saveFilterDescription}
                          onChange={(e) => setSaveFilterDescription(e.target.value)}
                        />
                      </div>
                      <div className="flex justify-end space-x-2">
                        <Button variant="outline" size="sm" onClick={() => setShowSaveDialog(false)}>
                          Cancel
                        </Button>
                        <Button size="sm" onClick={handleSaveFilter} disabled={!saveFilterName.trim()}>
                          Save
                        </Button>
                      </div>
                    </div>
                  </PopoverContent>
                </Popover>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Filters Panel */}
      {showAdvanced && (
        <Card>
          <CardHeader>
            <CardTitle>Advanced Filters</CardTitle>
            <CardDescription>
              Fine-tune your search with detailed criteria
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Permissions/Scopes */}
              <div className="space-y-2">
                <Label>Permissions</Label>
                <div className="border rounded-md p-3 max-h-32 overflow-y-auto">
                  {availableScopes.map((scope) => (
                    <div key={scope} className="flex items-center space-x-2 py-1">
                      <Checkbox
                        id={`scope-${scope}`}
                        checked={filters.scopes?.includes(scope) || false}
                        onCheckedChange={() => handleArrayFilter('scopes', scope, filters.scopes)}
                      />
                      <Label htmlFor={`scope-${scope}`} className="text-sm font-normal">
                        {scope}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              {/* Request Count Range */}
              <div className="space-y-2">
                <Label>Request Count</Label>
                <div className="space-y-2">
                  <Input
                    type="number"
                    placeholder="Min requests"
                    value={filters.minRequests || ''}
                    onChange={(e) => updateFilter('minRequests', e.target.value ? parseInt(e.target.value) : undefined)}
                  />
                  <Input
                    type="number"
                    placeholder="Max requests"
                    value={filters.maxRequests || ''}
                    onChange={(e) => updateFilter('maxRequests', e.target.value ? parseInt(e.target.value) : undefined)}
                  />
                </div>
              </div>

              {/* Key Features */}
              <div className="space-y-2">
                <Label>Key Features</Label>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="has-expiration"
                      checked={filters.hasExpiration === true}
                      onCheckedChange={(checked) => updateFilter('hasExpiration', checked ? true : undefined)}
                    />
                    <Label htmlFor="has-expiration" className="text-sm">Has expiration date</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="has-ip-restriction"
                      checked={filters.hasIpRestriction === true}
                      onCheckedChange={(checked) => updateFilter('hasIpRestriction', checked ? true : undefined)}
                    />
                    <Label htmlFor="has-ip-restriction" className="text-sm">Has IP restrictions</Label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="has-domain-restriction"
                      checked={filters.hasDomainRestriction === true}
                      onCheckedChange={(checked) => updateFilter('hasDomainRestriction', checked ? true : undefined)}
                    />
                    <Label htmlFor="has-domain-restriction" className="text-sm">Has domain restrictions</Label>
                  </div>
                </div>
              </div>
            </div>

            {/* Date Ranges */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4 border-t">
              <DateRangePicker
                label="Created Date"
                afterDate={filters.createdAfter}
                beforeDate={filters.createdBefore}
                onAfterChange={(date) => updateFilter('createdAfter', date)}
                onBeforeChange={(date) => updateFilter('createdBefore', date)}
              />
              
              <DateRangePicker
                label="Expiration Date"
                afterDate={filters.expiresAfter}
                beforeDate={filters.expiresBefore}
                onAfterChange={(date) => updateFilter('expiresAfter', date)}
                onBeforeChange={(date) => updateFilter('expiresBefore', date)}
              />
              
              <DateRangePicker
                label="Last Used Date"
                afterDate={filters.lastUsedAfter}
                beforeDate={filters.lastUsedBefore}
                onAfterChange={(date) => updateFilter('lastUsedAfter', date)}
                onBeforeChange={(date) => updateFilter('lastUsedBefore', date)}
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}