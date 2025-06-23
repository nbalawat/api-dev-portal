'use client'

import { useState, useEffect, useCallback } from 'react'
import { Search, X, Filter } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { motion, AnimatePresence } from 'framer-motion'

interface SearchBarProps {
  onSearch: (query: string, filters?: SearchFilters) => void
  placeholder?: string
  categories?: string[]
  methods?: string[]
}

export interface SearchFilters {
  categories: string[]
  methods: string[]
  requiresApiKey?: boolean
}

export function SearchBar({ 
  onSearch, 
  placeholder = "Search APIs by name, description, or tags...",
  categories = [],
  methods = ['GET', 'POST', 'PUT', 'DELETE']
}: SearchBarProps) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({
    categories: [],
    methods: [],
    requiresApiKey: undefined
  })
  const [showFilters, setShowFilters] = useState(false)
  const [isFocused, setIsFocused] = useState(false)

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query, filters)
    }, 300)

    return () => clearTimeout(timer)
  }, [query, filters, onSearch])

  const handleClearSearch = () => {
    setQuery('')
    setFilters({
      categories: [],
      methods: [],
      requiresApiKey: undefined
    })
  }

  const toggleCategory = (category: string) => {
    setFilters(prev => ({
      ...prev,
      categories: prev.categories.includes(category)
        ? prev.categories.filter(c => c !== category)
        : [...prev.categories, category]
    }))
  }

  const toggleMethod = (method: string) => {
    setFilters(prev => ({
      ...prev,
      methods: prev.methods.includes(method)
        ? prev.methods.filter(m => m !== method)
        : [...prev.methods, method]
    }))
  }

  const activeFiltersCount = 
    filters.categories.length + 
    filters.methods.length + 
    (filters.requiresApiKey !== undefined ? 1 : 0)

  return (
    <div className="w-full space-y-3">
      <motion.div 
        className={`
          relative flex items-center gap-2 
          ${isFocused ? 'ring-2 ring-primary ring-offset-2' : ''}
          rounded-xl transition-all duration-300
        `}
        animate={{
          scale: isFocused ? 1.01 : 1,
        }}
        transition={{ duration: 0.2 }}
      >
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground pointer-events-none" />
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            className="pl-10 pr-10 h-12 text-base border-2 border-border focus:border-primary bg-background backdrop-blur-sm rounded-xl transition-all duration-300"
          />
          <AnimatePresence>
            {query && (
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.15 }}
                onClick={handleClearSearch}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 hover:bg-muted rounded-md transition-colors"
              >
                <X className="h-4 w-4 text-muted-foreground" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>

        <Popover open={showFilters} onOpenChange={setShowFilters}>
          <PopoverTrigger asChild>
            <Button 
              variant="outline" 
              size="default"
              className="h-12 px-4 relative"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
              {activeFiltersCount > 0 && (
                <Badge 
                  variant="default" 
                  className="ml-2 h-5 w-5 p-0 flex items-center justify-center text-xs"
                >
                  {activeFiltersCount}
                </Badge>
              )}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-80 p-4" align="end">
            <div className="space-y-4">
              <div>
                <h4 className="font-medium mb-3">Filter by Category</h4>
                <div className="space-y-2">
                  {categories.map(category => (
                    <div key={category} className="flex items-center space-x-2">
                      <Checkbox
                        id={`category-${category}`}
                        checked={filters.categories.includes(category)}
                        onCheckedChange={() => toggleCategory(category)}
                      />
                      <Label 
                        htmlFor={`category-${category}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {category}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-3">Filter by Method</h4>
                <div className="grid grid-cols-2 gap-2">
                  {methods.map(method => (
                    <div key={method} className="flex items-center space-x-2">
                      <Checkbox
                        id={`method-${method}`}
                        checked={filters.methods.includes(method)}
                        onCheckedChange={() => toggleMethod(method)}
                      />
                      <Label 
                        htmlFor={`method-${method}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {method}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="font-medium mb-3">Other Filters</h4>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="requires-api-key"
                    checked={filters.requiresApiKey === true}
                    onCheckedChange={(checked) => 
                      setFilters(prev => ({
                        ...prev,
                        requiresApiKey: checked === true ? true : undefined
                      }))
                    }
                  />
                  <Label 
                    htmlFor="requires-api-key"
                    className="text-sm font-normal cursor-pointer"
                  >
                    Requires API Key
                  </Label>
                </div>
              </div>

              {activeFiltersCount > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setFilters({
                    categories: [],
                    methods: [],
                    requiresApiKey: undefined
                  })}
                  className="w-full"
                >
                  Clear All Filters
                </Button>
              )}
            </div>
          </PopoverContent>
        </Popover>
      </motion.div>

      {/* Active filters display */}
      <AnimatePresence>
        {activeFiltersCount > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="flex flex-wrap gap-2"
          >
            {filters.categories.map(category => (
              <Badge 
                key={`cat-${category}`} 
                variant="secondary"
                className="pl-3 pr-1 py-1 flex items-center gap-1"
              >
                {category}
                <button
                  onClick={() => toggleCategory(category)}
                  className="ml-1 p-0.5 hover:bg-muted rounded"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
            {filters.methods.map(method => (
              <Badge 
                key={`method-${method}`} 
                variant="outline"
                className="pl-3 pr-1 py-1 flex items-center gap-1"
              >
                {method}
                <button
                  onClick={() => toggleMethod(method)}
                  className="ml-1 p-0.5 hover:bg-muted rounded"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))}
            {filters.requiresApiKey === true && (
              <Badge 
                variant="outline"
                className="pl-3 pr-1 py-1 flex items-center gap-1"
              >
                API Key Required
                <button
                  onClick={() => setFilters(prev => ({ ...prev, requiresApiKey: undefined }))}
                  className="ml-1 p-0.5 hover:bg-muted rounded"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}