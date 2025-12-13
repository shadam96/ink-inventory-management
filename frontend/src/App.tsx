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
import { useAuthStore } from '@/store/auth'
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt'
import { initDB } from '@/lib/offline'

// Initialize IndexedDB on app load
initDB().catch(console.error)

// Placeholder for Settings page
function SettingsPage() {
  return (
    <div className="flex items-center justify-center h-[calc(100vh-6rem)]">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-2">הגדרות</h1>
        <p className="text-muted-foreground">עמוד זה בפיתוח</p>
      </div>
    </div>
  )
}

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
