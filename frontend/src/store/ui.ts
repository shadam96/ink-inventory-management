import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Currency = 'ILS' | 'USD' | 'EUR'

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'system'
  currency: Currency
  
  // Actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setCurrency: (currency: Currency) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      currency: 'ILS',
      
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      setCurrency: (currency) => set({ currency }),
    }),
    {
      name: 'ui-storage',
    }
  )
)

