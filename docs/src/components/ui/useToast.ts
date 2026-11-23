import { reactive } from 'vue'

export type ToastType = 'default' | 'success' | 'error'

export interface ToastItem {
  id: number
  message: string
  type: ToastType
}

interface ToastOptions {
  type?: ToastType
  /** Milliseconds before auto-dismiss. Use 0 to keep it open. */
  duration?: number
}

const state = reactive<{ items: ToastItem[] }>({ items: [] })
let sequence = 0

function dismiss(id: number): void {
  const index = state.items.findIndex((item) => item.id === id)
  if (index !== -1) state.items.splice(index, 1)
}

function push(message: string, options: ToastOptions = {}): number {
  const id = ++sequence
  state.items.push({ id, message, type: options.type ?? 'default' })
  const duration = options.duration ?? 2400
  if (duration > 0) window.setTimeout(() => dismiss(id), duration)
  return id
}

type ToastFn = {
  (message: string, options?: ToastOptions): number
  success: (message: string, options?: Omit<ToastOptions, 'type'>) => number
  error: (message: string, options?: Omit<ToastOptions, 'type'>) => number
}

export const toast = Object.assign(push, {
  success: (message: string, options: Omit<ToastOptions, 'type'> = {}) =>
    push(message, { ...options, type: 'success' }),
  error: (message: string, options: Omit<ToastOptions, 'type'> = {}) =>
    push(message, { ...options, type: 'error' }),
}) as ToastFn

export function useToast() {
  return { toasts: state.items, toast, dismiss }
}
