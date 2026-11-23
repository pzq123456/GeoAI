import { ref, watch, type Ref } from 'vue'

const STORAGE_KEY = 'geoai-theme'

function initialTheme(): boolean {
  if (typeof window === 'undefined') return false
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved === 'dark' || saved === 'light') return saved === 'dark'
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** 替代 VitePress 的 useData().isDark：纯 SPA 自己管理暗色状态。 */
export const isDark: Ref<boolean> = ref(initialTheme())

function applyTheme(value: boolean): void {
  if (typeof document === 'undefined') return
  document.documentElement.classList.toggle('dark', value)
  document.documentElement.style.colorScheme = value ? 'dark' : 'light'
  localStorage.setItem(STORAGE_KEY, value ? 'dark' : 'light')
}

applyTheme(isDark.value)
watch(isDark, applyTheme)

export function useTheme(): { isDark: Ref<boolean> } {
  return { isDark }
}
