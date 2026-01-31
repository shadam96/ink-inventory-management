import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Currency = 'ILS' | 'USD' | 'EUR'
type AppIcon = 'droplets' | 'package' | 'boxes' | 'warehouse'

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'system'
  currency: Currency
  appName: string
  appIcon: AppIcon
  
  // Actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setCurrency: (currency: Currency) => void
  setAppName: (name: string) => void
  setAppIcon: (icon: AppIcon) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      currency: 'ILS',
      appName: 'ניהול מלאי דיו',
      appIcon: 'droplets',
      
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      setCurrency: (currency) => set({ currency }),
      setAppName: (name) => set({ appName: name }),
      setAppIcon: (icon) => set({ appIcon: icon }),
    }),
    {
      name: 'ui-storage',
    }
  )
)

