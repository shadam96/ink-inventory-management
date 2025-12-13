import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Package,
  PackagePlus,
  PackageMinus,
  FileText,
  MoreHorizontal,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

const mainNavItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'דשבורד' },
  { to: '/receiving', icon: PackagePlus, label: 'קבלה' },
  { to: '/picking', icon: PackageMinus, label: 'ליקוט' },
  { to: '/delivery-notes', icon: FileText, label: 'תעודות' },
]

const moreNavItems = [
  { to: '/items', icon: Package, label: 'פריטים' },
  { to: '/batches', icon: Package, label: 'אצוות' },
  { to: '/customers', icon: Package, label: 'לקוחות' },
  { to: '/alerts', icon: Package, label: 'התראות' },
]

export function MobileNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const location = useLocation()

  const isMoreActive = moreNavItems.some((item) => location.pathname === item.to)

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-background border-t md:hidden safe-area-inset-bottom">
      <div className="flex items-center justify-around h-16">
        {mainNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors',
                isActive
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )
            }
          >
            <item.icon className="w-5 h-5" />
            <span className="text-[10px] font-medium">{item.label}</span>
          </NavLink>
        ))}

        <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
          <SheetTrigger asChild>
            <button
              className={cn(
                'flex flex-col items-center justify-center gap-1 flex-1 h-full transition-colors',
                isMoreActive
                  ? 'text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              <MoreHorizontal className="w-5 h-5" />
              <span className="text-[10px] font-medium">עוד</span>
            </button>
          </SheetTrigger>
          <SheetContent side="bottom" className="h-auto">
            <SheetHeader>
              <SheetTitle>תפריט נוסף</SheetTitle>
            </SheetHeader>
            <div className="grid grid-cols-4 gap-4 py-6">
              {moreNavItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMoreOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'flex flex-col items-center justify-center gap-2 p-4 rounded-lg transition-colors',
                      isActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-muted'
                    )
                  }
                >
                  <item.icon className="w-6 h-6" />
                  <span className="text-xs font-medium">{item.label}</span>
                </NavLink>
              ))}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </nav>
  )
}
