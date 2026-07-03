import { useState, useCallback, createContext, useContext } from 'react'
import type { Toast } from '../types'

interface ToastContextValue {
  toasts: Toast[]
  addToast: (message: string, type?: Toast['type']) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue>(null!)

export function useToast() {
  return useContext(ToastContext)
}

let _toastId = 0

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts(t => t.filter(x => x.id !== id))
  }, [])

  const addToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = `toast-${++_toastId}`
    setToasts(t => [...t, { id, message, type }])
    setTimeout(() => removeToast(id), 3000)
  }, [removeToast])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 items-center pointer-events-none">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`px-4 py-2 rounded-lg text-sm shadow-lg backdrop-blur-lg transition-all animate-fade-in pointer-events-auto ${
              t.type === 'error' ? 'bg-red-900/90 text-red-200' :
              t.type === 'warning' ? 'bg-amber-900/90 text-amber-200' :
              t.type === 'success' ? 'bg-green-900/90 text-green-200' :
              'bg-gray-800/90 text-gray-200'
            }`}
          >
            {t.type === 'error' ? '✕ ' : t.type === 'warning' ? '⚠ ' : t.type === 'success' ? '✓ ' : 'ℹ '}
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
