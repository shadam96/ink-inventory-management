import { NavLink } from 'react-router-dom'
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

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'דשבורד' },
  { to: '/receiving', icon: PackagePlus, label: 'קבלה' },
  { to: '/picking', icon: PackageMinus, label: 'ליקוט' },
  { to: '/delivery-notes', icon: FileText, label: 'תעודות' },
  { to: '/items', icon: Package, label: 'פריטים' },
  { to: '/batches', icon: Layers, label: 'אצוות' },
  { to: '/customers', icon: Users, label: 'לקוחות' },
  { to: '/alerts', icon: Bell, label: 'התראות' },
  { to: '/settings', icon: Settings, label: 'הגדרות' },
]

export function MobileNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-background/95 backdrop-blur-sm border-t md:hidden safe-area-inset-bottom">
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
            <span className="text-[10px] font-medium leading-tight">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
