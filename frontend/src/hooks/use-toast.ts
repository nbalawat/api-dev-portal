import React, { useState, useCallback } from 'react'

export interface Toast {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'destructive' | 'success'
  action?: React.ReactElement
  duration?: number
}

interface ToasterToast extends Toast {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const TOAST_LIMIT = 5
const TOAST_REMOVE_DELAY = 6000

let count = 0

function genId() {
  count = (count + 1) % Number.MAX_VALUE
  return count.toString()
}

type ToasterState = {
  toasts: ToasterToast[]
}

const toasterState: ToasterState = {
  toasts: []
}

let listeners: Array<(state: ToasterState) => void> = []

function dispatch(action: {
  type: 'ADD_TOAST' | 'UPDATE_TOAST' | 'DISMISS_TOAST' | 'REMOVE_TOAST'
  toast?: Partial<ToasterToast>
  toastId?: string
}) {
  switch (action.type) {
    case 'ADD_TOAST':
      toasterState.toasts = [action.toast, ...toasterState.toasts].slice(0, TOAST_LIMIT) as ToasterToast[]
      break
    case 'UPDATE_TOAST':
      toasterState.toasts = toasterState.toasts.map(t =>
        t.id === action.toast?.id ? { ...t, ...action.toast } : t
      )
      break
    case 'DISMISS_TOAST': {
      const { toastId } = action
      if (toastId) {
        addToRemoveQueue(toastId)
      } else {
        toasterState.toasts.forEach(toast => {
          addToRemoveQueue(toast.id)
        })
      }
      
      toasterState.toasts = toasterState.toasts.map(t =>
        t.id === toastId || toastId === undefined
          ? {
              ...t,
              open: false,
            }
          : t
      )
      break
    }
    case 'REMOVE_TOAST':
      if (action.toastId === undefined) {
        toasterState.toasts = []
      } else {
        toasterState.toasts = toasterState.toasts.filter(t => t.id !== action.toastId)
      }
      break
  }

  listeners.forEach(listener => {
    listener(toasterState)
  })
}

const removeToastQueue = new Map<string, ReturnType<typeof setTimeout>>()

const addToRemoveQueue = (toastId: string) => {
  if (removeToastQueue.has(toastId)) {
    return
  }

  const timeout = setTimeout(() => {
    removeToastQueue.delete(toastId)
    dispatch({
      type: 'REMOVE_TOAST',
      toastId: toastId,
    })
  }, TOAST_REMOVE_DELAY)

  removeToastQueue.set(toastId, timeout)
}

export const toast = ({ ...props }: Omit<ToasterToast, 'id' | 'open' | 'onOpenChange'>) => {
  const id = genId()

  const update = (props: ToasterToast) =>
    dispatch({
      type: 'UPDATE_TOAST',
      toast: { ...props, id },
    })
  const dismiss = () => dispatch({ type: 'DISMISS_TOAST', toastId: id })

  dispatch({
    type: 'ADD_TOAST',
    toast: {
      ...props,
      id,
      open: true,
      onOpenChange: (open: boolean) => {
        if (!open) dismiss()
      },
    },
  })

  return {
    id: id,
    dismiss,
    update,
  }
}

export function useToast() {
  const [state, setState] = useState<ToasterState>(toasterState)

  React.useEffect(() => {
    listeners.push(setState)
    return () => {
      const index = listeners.indexOf(setState)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }, [state])

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => dispatch({ type: 'DISMISS_TOAST', toastId }),
  }
}