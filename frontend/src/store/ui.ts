import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Currency = 'ILS' | 'USD' | 'EUR' | 'TRY'
type AppIcon = 'droplets' | 'package' | 'boxes' | 'warehouse'

/**
 * Default app name. Intentionally locale-neutral — `appName` is a user-set
 * personalization (their company / brand) and is *not* auto-translated.
 */
export const DEFAULT_APP_NAME = 'Lino Print'

/** Legacy Hebrew default that shipped before i18n. Used by the migration. */
const LEGACY_HEBREW_APP_NAME = 'ניהול מלאי דיו'

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
      appName: DEFAULT_APP_NAME,
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
      version: 2,
      // v1 → v2: replace the legacy Hebrew default app name with a neutral
      // brand. Users who customized `appName` keep their value untouched.
      migrate: (persistedState, fromVersion) => {
        const state = (persistedState as Partial<UIState> | undefined) ?? {}
        if (fromVersion < 2) {
          if (!state.appName || state.appName === LEGACY_HEBREW_APP_NAME) {
            state.appName = DEFAULT_APP_NAME
          }
        }
        return state as UIState
      },
    },
  ),
)

