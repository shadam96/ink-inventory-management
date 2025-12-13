import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { useUIStore } from '@/store/ui'
import { cn } from '@/lib/utils'
import { MobileNav } from '@/components/MobileNav'
import { OfflineIndicator } from '@/components/OfflineIndicator'
import { PWAInstallPrompt } from '@/components/PWAInstallPrompt'

export function AppLayout() {
  const { sidebarOpen } = useUIStore()

  return (
    <div dir="rtl" className="min-h-screen bg-background">
      {/* Desktop sidebar */}
      <div className="hidden md:block">
        <Sidebar />
      </div>
      
      {/* Offline indicator */}
      <div className="fixed top-4 left-4 z-40 hidden md:block">
        <OfflineIndicator />
      </div>
      
      <main
        className={cn(
          'min-h-screen transition-all duration-300',
          // Desktop: margin for sidebar
          'md:mr-16',
          sidebarOpen && 'md:mr-64',
          // Mobile: no margin, padding for bottom nav
          'pb-20 md:pb-0'
        )}
      >
        <div className="p-4 md:p-6 pt-4 md:pt-6">
          <Outlet />
        </div>
      </main>

      {/* Mobile bottom navigation */}
      <MobileNav />

      {/* PWA Install Prompt */}
      <PWAInstallPrompt />

      {/* Mobile offline indicator */}
      <div className="md:hidden">
        <OfflineIndicator />
      </div>
    </div>
  )
}
