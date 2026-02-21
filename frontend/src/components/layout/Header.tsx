import { useTranslation } from 'react-i18next'
import { NotificationBell } from '@/components/NotificationBell'
import { useUIStore } from '@/store/ui'
import { cn } from '@/lib/utils'

interface HeaderProps {
  title: string
}

export function Header({ title }: HeaderProps) {
  const { t } = useTranslation()
  const { sidebarOpen } = useUIStore()

  return (
    <header
      className={cn(
        'fixed top-0 left-0 z-40 h-16 bg-background/95 backdrop-blur border-b transition-all duration-300',
        sidebarOpen ? 'right-64' : 'right-16'
      )}
    >
      <div className="flex items-center justify-between h-full px-6">
        <h1 className="text-xl font-semibold">{title}</h1>

        <div className="flex items-center gap-4">
          <NotificationBell />
        </div>
      </div>
    </header>
  )
}

