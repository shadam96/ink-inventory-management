import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { InventoryPage } from '@/pages/InventoryPage'
import { ItemsPage } from '@/pages/ItemsPage'
import { BatchesPage } from '@/pages/BatchesPage'
import { ReceivingPage } from '@/pages/ReceivingPage'
import { PickingPage } from '@/pages/PickingPage'
import { DeliveryNotesPage } from '@/pages/DeliveryNotesPage'
import { CustomersPage } from '@/pages/CustomersPage'
import { AlertsPage } from '@/pages/AlertsPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt'
import { initDB } from '@/lib/offline'

// Initialize IndexedDB on app load
initDB().catch(console.error)

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, fetchUser } = useAuthStore()
  const token = localStorage.getItem('access_token')

  // isAuthenticated is persisted across reloads, but `user` is not (see
  // partialize in store/auth.ts) - so isAuthenticated alone can be stale
  // true while `user` is still null in memory. Gate on `user` instead, or
  // fetchUser() never fires and StaffRoute's "loading" null-render below
  // becomes permanent.
  useEffect(() => {
    if (token && !user) {
      fetchUser()
    }
  }, [token, user, fetchUser])

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

export function StaffRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuthStore()
  const token = localStorage.getItem('access_token')

  // The persisted auth store only rehydrates isAuthenticated, not `user` -
  // on a page reload, user starts null until ProtectedRoute's fetchUser()
  // resolves. Rendering nothing during that window (instead of assuming
  // "not a customer" and rendering/fetching staff-only data) avoids a
  // customer-role user briefly seeing/fetching staff-only routes.
  if (token && isAuthenticated && user === null) {
    return null
  }

  if (user?.role === 'customer') {
    return <Navigate to="/picking" replace />
  }

  return <>{children}</>
}

function App() {
  const { theme } = useUIStore()

  // Apply theme on mount and when it changes
  useEffect(() => {
    const applyTheme = () => {
      const root = document.documentElement

      // Add transition class for smooth theme switching
      root.classList.add('theme-transition')

      if (theme === 'system') {
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        root.classList.toggle('dark', systemTheme === 'dark')
      } else {
        root.classList.toggle('dark', theme === 'dark')
      }

      // Remove transition class after animation completes
      setTimeout(() => root.classList.remove('theme-transition'), 350)
    }

    applyTheme()

    // Listen for system theme changes when in system mode
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      const handleChange = () => applyTheme()
      mediaQuery.addEventListener('change', handleChange)
      return () => mediaQuery.removeEventListener('change', handleChange)
    }
  }, [theme])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<StaffRoute><DashboardPage /></StaffRoute>} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="items" element={<StaffRoute><ItemsPage /></StaffRoute>} />
          <Route path="batches" element={<StaffRoute><BatchesPage /></StaffRoute>} />
          <Route path="receiving" element={<StaffRoute><ReceivingPage /></StaffRoute>} />
          <Route path="picking" element={<PickingPage />} />
          <Route path="delivery-notes" element={<StaffRoute><DeliveryNotesPage /></StaffRoute>} />
          <Route path="customers" element={<StaffRoute><CustomersPage /></StaffRoute>} />
          <Route path="alerts" element={<StaffRoute><AlertsPage /></StaffRoute>} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      {/* PWA Install Prompt */}
      <PWAInstallPrompt />
    </BrowserRouter>
  )
}

export default App
