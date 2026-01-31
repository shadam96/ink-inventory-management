import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
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
  const { isAuthenticated, fetchUser } = useAuthStore()
  const token = localStorage.getItem('access_token')

  useEffect(() => {
    if (token && !isAuthenticated) {
      fetchUser()
    }
  }, [token, isAuthenticated, fetchUser])

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function App() {
  const { theme } = useUIStore()

  // Apply theme on mount and when it changes
  useEffect(() => {
    const applyTheme = () => {
      const root = document.documentElement
      
      if (theme === 'system') {
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        root.classList.toggle('dark', systemTheme === 'dark')
      } else {
        root.classList.toggle('dark', theme === 'dark')
      }
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
          <Route index element={<DashboardPage />} />
          <Route path="items" element={<ItemsPage />} />
          <Route path="batches" element={<BatchesPage />} />
          <Route path="receiving" element={<ReceivingPage />} />
          <Route path="picking" element={<PickingPage />} />
          <Route path="delivery-notes" element={<DeliveryNotesPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="alerts" element={<AlertsPage />} />
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
