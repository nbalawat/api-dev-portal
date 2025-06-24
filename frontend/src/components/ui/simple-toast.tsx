'use client'

import { useEffect, useState } from 'react'
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface Toast {
  id: string
  title: string
  description?: string
  variant?: 'default' | 'destructive' | 'success'
  duration?: number
}

class ToastManager {
  private listeners: ((toasts: Toast[]) => void)[] = []
  private toasts: Toast[] = []

  subscribe(listener: (toasts: Toast[]) => void) {
    this.listeners.push(listener)
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener)
    }
  }

  show(toast: Omit<Toast, 'id'>) {
    const id = Date.now().toString()
    const newToast = { ...toast, id }
    this.toasts = [...this.toasts, newToast]
    this.notify()

    // Auto remove after duration
    setTimeout(() => {
      this.remove(id)
    }, toast.duration || 5000)
  }

  remove(id: string) {
    this.toasts = this.toasts.filter(t => t.id !== id)
    this.notify()
  }

  private notify() {
    this.listeners.forEach(listener => listener([...this.toasts]))
  }
}

export const toastManager = new ToastManager()

export function showToast(options: Omit<Toast, 'id'>) {
  toastManager.show(options)
}

export function SimpleToaster() {
  const [toasts, setToasts] = useState<Toast[]>([])

  useEffect(() => {
    return toastManager.subscribe(setToasts)
  }, [])

  const getIcon = (variant?: string) => {
    switch (variant) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'destructive':
        return <AlertCircle className="w-5 h-5 text-red-600" />
      default:
        return <Info className="w-5 h-5 text-blue-600" />
    }
  }

  const getStyles = (variant?: string) => {
    switch (variant) {
      case 'success':
        return 'bg-white border-green-200 shadow-green-100'
      case 'destructive':
        return 'bg-white border-red-200 shadow-red-100'
      default:
        return 'bg-white border-blue-200 shadow-blue-100'
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-lg border shadow-lg max-w-sm ${getStyles(toast.variant)}`}
          >
            {getIcon(toast.variant)}
            <div className="flex-1">
              <p className="font-semibold text-gray-900">{toast.title}</p>
              {toast.description && (
                <p className="text-sm text-gray-600 mt-1">{toast.description}</p>
              )}
            </div>
            <button
              onClick={() => toastManager.remove(toast.id)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}