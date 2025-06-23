"use client"

import React, { useState, useCallback, useEffect } from 'react'
import { Search, Filter, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'

interface MarketplaceSearchProps {
  onSearch: (query: string, filters: SearchFilters) => void
  categories?: string[]
  tags?: string[]
  className?: string
}

interface SearchFilters {
  category?: string
  tag?: string
  method?: string
}

const httpMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'] as const

export function MarketplaceSearch({
  onSearch,
  categories = [],
  tags = [],
  className
}: MarketplaceSearchProps) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [isFiltersOpen, setIsFiltersOpen] = useState(false)
  const [isFocused, setIsFocused] = useState(false)

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query, filters)
    }, 300)

    return () => clearTimeout(timer)
  }, [query, filters, onSearch])

  const handleClearSearch = useCallback(() => {
    setQuery('')
    setFilters({})
  }, [])

  const handleFilterChange = useCallback((key: keyof SearchFilters, value: string | undefined) => {
    setFilters(prev => ({
      ...prev,
      [key]: value === 'all' ? undefined : value
    }))
  }, [])

  const activeFiltersCount = Object.values(filters).filter(Boolean).length

  return (
    <div className={cn("w-full", className)}>
      <div className="relative">
        <motion.div
          className={cn(
            "relative flex items-center gap-2 rounded-2xl border-2 transition-all duration-300",
            "bg-background/95 backdrop-blur-sm",
            isFocused ? "border-primary shadow-lg shadow-primary/20" : "border-border",
            "hover:border-primary/50"
          )}
          initial={false}
          animate={{
            scale: isFocused ? 1.02 : 1,
          }}
          transition={{ duration: 0.2 }}
        >
          <div className="flex-1 relative">
            <Search className={cn(
              "absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 transition-colors duration-200",
              isFocused ? "text-primary" : "text-muted-foreground"
            )} />
            <Input
              type="text"
              placeholder="Search APIs, endpoints, or documentation..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              className="pl-12 pr-4 py-6 text-base border-0 bg-transparent focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>
          
          <div className="flex items-center gap-2 pr-2">
            <AnimatePresence>
              {(query || activeFiltersCount > 0) && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  transition={{ duration: 0.15 }}
                >
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearSearch}
                    className="h-8 px-2"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
            
            <Button
              variant={isFiltersOpen ? "default" : "outline"}
              size="sm"
              onClick={() => setIsFiltersOpen(!isFiltersOpen)}
              className="relative h-10 px-4"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
              {activeFiltersCount > 0 && (
                <Badge
                  variant="gradient"
                  size="sm"
                  className="absolute -top-2 -right-2 h-5 w-5 p-0 flex items-center justify-center"
                >
                  {activeFiltersCount}
                </Badge>
              )}
            </Button>
          </div>
        </motion.div>

        <AnimatePresence>
          {isFiltersOpen && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="absolute top-full left-0 right-0 mt-2 p-6 rounded-2xl border-2 border-border bg-background/95 backdrop-blur-sm shadow-xl z-50"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">
                    Category
                  </label>
                  <Select
                    value={filters.category || 'all'}
                    onValueChange={(value) => handleFilterChange('category', value)}
                  >
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue placeholder="All Categories" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="all" className="rounded-lg">All Categories</SelectItem>
                      {categories.map(category => (
                        <SelectItem key={category} value={category} className="rounded-lg">
                          {category}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">
                    HTTP Method
                  </label>
                  <Select
                    value={filters.method || 'all'}
                    onValueChange={(value) => handleFilterChange('method', value)}
                  >
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue placeholder="All Methods" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="all" className="rounded-lg">All Methods</SelectItem>
                      {httpMethods.map(method => (
                        <SelectItem key={method} value={method} className="rounded-lg">
                          <Badge variant="outline" className="font-mono">
                            {method}
                          </Badge>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <label className="text-sm font-medium text-muted-foreground mb-2 block">
                    Tag
                  </label>
                  <Select
                    value={filters.tag || 'all'}
                    onValueChange={(value) => handleFilterChange('tag', value)}
                  >
                    <SelectTrigger className="h-11 rounded-xl">
                      <SelectValue placeholder="All Tags" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                      <SelectItem value="all" className="rounded-lg">All Tags</SelectItem>
                      {tags.map(tag => (
                        <SelectItem key={tag} value={tag} className="rounded-lg">
                          {tag}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {activeFiltersCount > 0 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-4 pt-4 border-t border-border flex items-center justify-between"
                >
                  <span className="text-sm text-muted-foreground">
                    {activeFiltersCount} filter{activeFiltersCount > 1 ? 's' : ''} applied
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setFilters({})}
                    className="text-sm"
                  >
                    Clear all filters
                  </Button>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}