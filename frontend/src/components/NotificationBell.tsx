import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, X, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import api from '@/lib/api'
import { useAlertNotifications } from '@/hooks/useWebSocket'

interface Alert {
  id: string
  type: string
  severity: string
  title: string
  message: string
  created_at: string
  is_read: boolean
}

export function NotificationBell() {
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)

  // Fetch initial alerts
  useEffect(() => {
    fetchAlerts()
  }, [])

  // Subscribe to real-time alert notifications
  useAlertNotifications((newAlert: Alert) => {
    // Add new alert to the beginning of the list
    setAlerts((prev) => [newAlert, ...prev].slice(0, 10))
    setUnreadCount((prev) => prev + 1)
    
    // Show toast notification (optional)
    console.log('New alert received:', newAlert)
  })

  const fetchAlerts = async () => {
    try {
      setLoading(true)
      const response = await api.get('/alerts', {
        params: { page: 1, page_size: 10, is_read: false },
      })
      setAlerts(response.data.items || [])
      setUnreadCount(response.data.items?.filter((a: Alert) => !a.is_read).length || 0)
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const markAsRead = async (alertId: string) => {
    try {
      await api.put(`/alerts/${alertId}/read`)
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, is_read: true } : alert
        )
      )
      setUnreadCount((prev) => Math.max(0, prev - 1))
    } catch (error) {
      console.error('Failed to mark alert as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      await api.put('/alerts/read-all')
      setAlerts((prev) => prev.map((alert) => ({ ...alert, is_read: true })))
      setUnreadCount(0)
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200'
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'info':
        return 'bg-blue-100 text-blue-800 border-blue-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diff = Math.floor((now.getTime() - time.getTime()) / 1000)

    if (diff < 60) return 'כרגע'
    if (diff < 3600) return `לפני ${Math.floor(diff / 60)} דקות`
    if (diff < 86400) return `לפני ${Math.floor(diff / 3600)} שעות`
    return `לפני ${Math.floor(diff / 86400)} ימים`
  }

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setIsOpen(!isOpen)}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 w-5 h-5 p-0 flex items-center justify-center text-xs"
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </Badge>
        )}
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <Card className="absolute left-0 top-12 w-96 z-50 shadow-lg">
            <div className="p-4 flex items-center justify-between border-b">
              <h3 className="font-semibold">התראות</h3>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllAsRead}
                    className="h-8 text-xs"
                  >
                    <Check className="w-4 h-4 ml-1" />
                    סמן הכל כנקרא
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => setIsOpen(false)}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            </div>

            <ScrollArea className="h-96">
              {loading ? (
                <div className="p-4 text-center text-muted-foreground">
                  טוען...
                </div>
              ) : alerts.length === 0 ? (
                <div className="p-8 text-center text-muted-foreground">
                  <Bell className="w-12 h-12 mx-auto mb-2 opacity-30" />
                  <p>אין התראות חדשות</p>
                </div>
              ) : (
                <div className="divide-y">
                  {alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${
                        !alert.is_read ? 'bg-blue-50/50' : ''
                      }`}
                      onClick={() => {
                        markAsRead(alert.id)
                        setIsOpen(false)
                        navigate('/alerts')
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full border ${getSeverityColor(
                                alert.severity
                              )}`}
                            >
                              {alert.severity === 'CRITICAL'
                                ? 'קריטי'
                                : alert.severity === 'WARNING'
                                ? 'אזהרה'
                                : 'מידע'}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {getTimeAgo(alert.created_at)}
                            </span>
                          </div>
                          <h4 className="font-medium text-sm mb-1">
                            {alert.title}
                          </h4>
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {alert.message}
                          </p>
                        </div>
                        {!alert.is_read && (
                          <div className="w-2 h-2 bg-cyan-500 rounded-full mt-1" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>

            <Separator />

            <div className="p-3">
              <Button
                variant="ghost"
                className="w-full"
                onClick={() => {
                  setIsOpen(false)
                  navigate('/alerts')
                }}
              >
                צפה בכל ההתראות
              </Button>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
