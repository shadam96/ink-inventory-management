import { useTranslation } from 'react-i18next'
import { Bell, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useUIStore } from '@/store/ui'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title: string
  alertCount?: number
}

export function Header({ title, alertCount = 0 }: HeaderProps) {
  const { t } = useTranslation()
  const { sidebarOpen } = useUIStore()

  return (
    <header
      className={cn(
        'fixed top-0 left-0 z-30 h-16 bg-background/95 backdrop-blur border-b transition-all duration-300',
        sidebarOpen ? 'right-64' : 'right-16'
      )}
    >
      <div className="flex items-center justify-between h-full px-6">
        <h1 className="text-xl font-semibold">{title}</h1>

        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="relative hidden md:block">
            <Search className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder={t('common.search')}
              className="w-64 pr-9"
            />
          </div>

          {/* Alerts */}
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="w-5 h-5" />
            {alertCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 w-5 h-5 p-0 flex items-center justify-center text-xs"
              >
                {alertCount > 9 ? '9+' : alertCount}
              </Badge>
            )}
          </Button>
        </div>
      </div>
    </header>
  )
}

