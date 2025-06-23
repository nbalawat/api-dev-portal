'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { DEFAULT_TEMPLATES, KeyTemplate, TemplateCategory, CreateKeyFromTemplateData } from '@/types/templates';
import { Clock, Shield, Zap, Settings, ChevronRight, Check } from 'lucide-react';

interface TemplateSelectorProps {
  onCreateKey: (data: CreateKeyFromTemplateData) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function TemplateSelector({ onCreateKey, onCancel, isLoading }: TemplateSelectorProps) {
  const [selectedTemplate, setSelectedTemplate] = useState<KeyTemplate | null>(null);
  const [customization, setCustomization] = useState<Partial<CreateKeyFromTemplateData>>({});
  const [step, setStep] = useState<'select' | 'customize'>('select');

  const handleTemplateSelect = (template: KeyTemplate) => {
    setSelectedTemplate(template);
    setCustomization({
      templateId: template.id,
      name: '',
      description: template.description,
      customScopes: template.defaultScopes,
      customExpirationDays: template.defaultExpirationDays,
      customRateLimit: template.rateLimit,
    });
    setStep('customize');
  };

  const handleCreateKey = () => {
    if (!selectedTemplate || !customization.name) return;
    
    onCreateKey({
      templateId: selectedTemplate.id,
      name: customization.name,
      description: customization.description,
      customScopes: customization.customScopes,
      customExpirationDays: customization.customExpirationDays,
      customRateLimit: customization.customRateLimit,
      customAllowedIps: customization.customAllowedIps,
      customAllowedDomains: customization.customAllowedDomains,
    });
  };

  const TemplateCard = ({ template }: { template: KeyTemplate }) => (
    <Card 
      className="cursor-pointer hover:shadow-md transition-shadow border-2 hover:border-blue-300"
      onClick={() => handleTemplateSelect(template)}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{template.icon}</span>
            <div>
              <CardTitle className="text-lg">{template.name}</CardTitle>
              <Badge className={template.color} variant="secondary">
                {template.environment}
              </Badge>
            </div>
          </div>
          <ChevronRight className="h-5 w-5 text-gray-400" />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <CardDescription className="mb-3">{template.description}</CardDescription>
        
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="flex items-center text-gray-600">
              <Clock className="h-4 w-4 mr-1" />
              Expires in
            </span>
            <span className="font-medium">{template.defaultExpirationDays} days</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="flex items-center text-gray-600">
              <Zap className="h-4 w-4 mr-1" />
              Rate limit
            </span>
            <span className="font-medium">
              {template.rateLimit}/{template.rateLimitPeriod}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="flex items-center text-gray-600">
              <Shield className="h-4 w-4 mr-1" />
              Scopes
            </span>
            <span className="font-medium">{template.defaultScopes.length} permissions</span>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-1 mt-3">
          {template.defaultScopes.slice(0, 3).map((scope) => (
            <Badge key={scope} variant="outline" className="text-xs">
              {scope}
            </Badge>
          ))}
          {template.defaultScopes.length > 3 && (
            <Badge variant="outline" className="text-xs">
              +{template.defaultScopes.length - 3} more
            </Badge>
          )}
        </div>
      </CardContent>
    </Card>
  );

  const CustomizationForm = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Customize API Key</h3>
          <p className="text-sm text-gray-600">
            Based on template: <span className="font-medium">{selectedTemplate?.name}</span>
          </p>
        </div>
        <Button variant="outline" onClick={() => setStep('select')}>
          Change Template
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <Label htmlFor="keyName">API Key Name *</Label>
            <Input
              id="keyName"
              placeholder="e.g., My Production App Key"
              value={customization.name || ''}
              onChange={(e) => setCustomization({ ...customization, name: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="keyDescription">Description</Label>
            <Textarea
              id="keyDescription"
              placeholder="Describe what this key will be used for..."
              value={customization.description || ''}
              onChange={(e) => setCustomization({ ...customization, description: e.target.value })}
            />
          </div>

          <div>
            <Label htmlFor="expirationDays">Expiration (days)</Label>
            <Input
              id="expirationDays"
              type="number"
              min="1"
              max="365"
              value={customization.customExpirationDays || ''}
              onChange={(e) => setCustomization({ 
                ...customization, 
                customExpirationDays: parseInt(e.target.value) || undefined 
              })}
            />
          </div>

          <div>
            <Label htmlFor="rateLimit">Rate Limit (requests/hour)</Label>
            <Input
              id="rateLimit"
              type="number"
              min="1"
              value={customization.customRateLimit || ''}
              onChange={(e) => setCustomization({ 
                ...customization, 
                customRateLimit: parseInt(e.target.value) || undefined 
              })}
            />
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <Label>Permissions</Label>
            <div className="border rounded-md p-3 max-h-40 overflow-y-auto">
              {['read', 'write', 'admin', 'user:profile', 'user:manage', 'webhook', 'analytics'].map((scope) => (
                <div key={scope} className="flex items-center space-x-2 py-1">
                  <Checkbox
                    id={scope}
                    checked={customization.customScopes?.includes(scope) || false}
                    onCheckedChange={(checked) => {
                      const currentScopes = customization.customScopes || [];
                      if (checked) {
                        setCustomization({
                          ...customization,
                          customScopes: [...currentScopes, scope]
                        });
                      } else {
                        setCustomization({
                          ...customization,
                          customScopes: currentScopes.filter(s => s !== scope)
                        });
                      }
                    }}
                  />
                  <Label htmlFor={scope} className="text-sm font-normal">
                    {scope}
                  </Label>
                </div>
              ))}
            </div>
          </div>

          <div>
            <Label htmlFor="allowedIps">Allowed IPs (optional)</Label>
            <Textarea
              id="allowedIps"
              placeholder="192.168.1.1, 10.0.0.0/8"
              value={customization.customAllowedIps?.join(', ') || ''}
              onChange={(e) => setCustomization({
                ...customization,
                customAllowedIps: e.target.value.split(',').map(ip => ip.trim()).filter(Boolean)
              })}
            />
          </div>

          <div>
            <Label htmlFor="allowedDomains">Allowed Domains (optional)</Label>
            <Textarea
              id="allowedDomains"
              placeholder="example.com, api.example.com"
              value={customization.customAllowedDomains?.join(', ') || ''}
              onChange={(e) => setCustomization({
                ...customization,
                customAllowedDomains: e.target.value.split(',').map(domain => domain.trim()).filter(Boolean)
              })}
            />
          </div>
        </div>
      </div>

      <div className="flex justify-between pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <div className="space-x-2">
          <Button variant="outline" onClick={() => setStep('select')}>
            Back
          </Button>
          <Button 
            onClick={handleCreateKey} 
            disabled={!customization.name || isLoading}
          >
            {isLoading ? 'Creating...' : 'Create API Key'}
          </Button>
        </div>
      </div>
    </div>
  );

  if (step === 'customize') {
    return <CustomizationForm />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Create API Key from Template</h2>
        <p className="text-gray-600 mt-1">
          Choose a pre-configured template to quickly create an API key with the right permissions and settings.
        </p>
      </div>

      <Tabs defaultValue={DEFAULT_TEMPLATES[0].id} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          {DEFAULT_TEMPLATES.map((category) => (
            <TabsTrigger key={category.id} value={category.id}>
              {category.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {DEFAULT_TEMPLATES.map((category) => (
          <TabsContent key={category.id} value={category.id} className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold">{category.name}</h3>
              <p className="text-sm text-gray-600">{category.description}</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {category.templates.map((template) => (
                <TemplateCard key={template.id} template={template} />
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>

      <div className="flex justify-between pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="outline">
          <Settings className="h-4 w-4 mr-2" />
          Create Custom Key
        </Button>
      </div>
    </div>
  );
}