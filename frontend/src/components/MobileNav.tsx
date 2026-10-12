import { NavLink } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
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
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/store/auth'

// Labels are i18n keys; resolved with `t()` at render time so the
// nav re-translates when the user switches language.
const allNavItems = [
  { to: '/', icon: LayoutDashboard, labelKey: 'nav.dashboard', staffOnly: true },
  { to: '/receiving', icon: PackagePlus, labelKey: 'nav.receiving', staffOnly: true },
  { to: '/picking', icon: PackageMinus, labelKey: 'nav.picking', staffOnly: false },
  { to: '/delivery-notes', icon: FileText, labelKey: 'nav.deliveryNotesShort', staffOnly: true },
  { to: '/items', icon: Package, labelKey: 'nav.items', staffOnly: true },
  { to: '/batches', icon: Layers, labelKey: 'nav.batches', staffOnly: true },
  { to: '/customers', icon: Users, labelKey: 'nav.customers', staffOnly: true },
  { to: '/alerts', icon: Bell, labelKey: 'nav.alerts', staffOnly: true },
  { to: '/users', icon: Users, labelKey: 'nav.users', staffOnly: true, adminOnly: true },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings', staffOnly: false },
]

export function MobileNav() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const isCustomer = user?.role === 'customer'
  const isAdmin = user?.role === 'admin'
  const navItems = allNavItems.filter(
    (item) => (!item.staffOnly || !isCustomer) && (!item.adminOnly || isAdmin)
  )

  return (
    <nav className="fixed bottom-0 inset-x-0 z-50 bg-background/95 backdrop-blur-sm border-t md:hidden safe-area-inset-bottom">
      <div
        className="flex overflow-x-auto scrollbar-hide snap-x snap-mandatory"
        style={{ WebkitOverflowScrolling: 'touch' }}
      >
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center justify-center gap-1 min-w-[4.5rem] py-2.5 px-2 snap-start transition-colors shrink-0',
                isActive
                  ? 'text-primary'
                  : 'text-muted-foreground active:text-foreground'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] font-medium leading-tight">{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
