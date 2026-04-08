import { Moon, Sun } from 'lucide-react'
import { NotificationBell } from '@/components/NotificationBell'
import { Button } from '@/components/ui/button'
import { useUIStore } from '@/store/ui'
import { cn } from '@/lib/utils'

export interface HeaderProps {
  title: string
  alertCount?: number
}

export function Header({ title }: HeaderProps) {
  const { sidebarOpen, theme, setTheme } = useUIStore()

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header
      className={cn(
        'fixed top-0 end-0 z-40 h-16 bg-background/95 backdrop-blur border-b transition-all duration-300',
        sidebarOpen ? 'start-64' : 'start-16'
      )}
    >
      <div className="flex items-center justify-between h-full px-6">
        <h1 className="text-xl font-semibold">{title}</h1>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'מצב בהיר' : 'מצב כהה'}
          >
            {theme === 'dark' ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
          </Button>
          <NotificationBell />
        </div>
      </div>
    </header>
  )
}

