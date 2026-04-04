import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import {
  LayoutDashboard,
  Package,
  Layers,
  PackagePlus,
  PackageMinus,
  FileText,
  Users,
  Bell,
  Settings,
  LogOut,
  ChevronRight,
  Droplets,
  Boxes,
  Warehouse,
} from 'lucide-react'

const allNavItems = [
  { path: '/', icon: LayoutDashboard, label: 'nav.dashboard', staffOnly: true },
  { path: '/items', icon: Package, label: 'nav.items', staffOnly: true },
  { path: '/batches', icon: Layers, label: 'nav.batches', staffOnly: true },
  { path: '/receiving', icon: PackagePlus, label: 'nav.receiving', staffOnly: true },
  { path: '/picking', icon: PackageMinus, label: 'nav.picking', staffOnly: false },
  { path: '/delivery-notes', icon: FileText, label: 'nav.deliveryNotes', staffOnly: true },
  { path: '/customers', icon: Users, label: 'nav.customers', staffOnly: true },
  { path: '/alerts', icon: Bell, label: 'nav.alerts', staffOnly: true },
]

const iconMap = {
  droplets: Droplets,
  package: Package,
  boxes: Boxes,
  warehouse: Warehouse,
}

export function Sidebar() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { sidebarOpen, toggleSidebar, appName, appIcon } = useUIStore()
  
  const IconComponent = iconMap[appIcon] || Droplets
  const isCustomer = user?.role === 'customer'
  const navItems = isCustomer
    ? allNavItems.filter(item => !item.staffOnly)
    : allNavItems

  return (
    <aside
      className={cn(
        'fixed top-0 right-0 z-40 h-screen bg-card border-l transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      <div className="flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center gap-3 p-4 border-b">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg gradient-ink">
            <IconComponent className="w-6 h-6 text-white" />
          </div>
          {sidebarOpen && (
            <div className="flex-1 animate-fade-in">
              <h1 className="font-bold text-lg">{appName}</h1>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="shrink-0"
          >
            <ChevronRight
              className={cn(
                'w-4 h-4 transition-transform',
                sidebarOpen && 'rotate-180'
              )}
            />
          </Button>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav className="space-y-4 px-2">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-accent'
                  )
                }
              >
                <item.icon className="w-5 h-5 shrink-0" />
                {sidebarOpen && (
                  <span className="animate-fade-in">{t(item.label)}</span>
                )}
              </NavLink>
            ))}
          </nav>
        </ScrollArea>

        <Separator />

        {/* User & Settings */}
        <div className="p-2 space-y-4">
          <NavLink
            to="/settings"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent'
              )
            }
          >
            <Settings className="w-5 h-5 shrink-0" />
            {sidebarOpen && (
              <span className="animate-fade-in">{t('nav.settings')}</span>
            )}
          </NavLink>

          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
              <span className="text-sm font-medium">
                {user?.full_name?.charAt(0) || 'U'}
              </span>
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0 animate-fade-in">
                <p className="text-sm font-medium truncate">{user?.full_name}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {user?.role}
                </p>
              </div>
            )}
          </div>

          <Button
            variant="ghost"
            className={cn(
              'w-full justify-start gap-3 text-destructive hover:text-destructive hover:bg-destructive/10',
              !sidebarOpen && 'justify-center'
            )}
            onClick={logout}
          >
            <LogOut className="w-5 h-5 shrink-0" />
            {sidebarOpen && <span>{t('nav.logout')}</span>}
          </Button>
        </div>
      </div>
    </aside>
  )
}

