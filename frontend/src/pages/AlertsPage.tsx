import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Bell, CheckCheck, AlertTriangle, Package, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { he } from 'date-fns/locale'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Header } from '@/components/layout/Header'
import { ScrollArea } from '@/components/ui/scroll-area'
import { alertsApi } from '@/lib/api'

interface Alert {
  id: string
  alert_type: string
  severity: string
  title: string
  message: string
  is_read: boolean
  created_at: string
}

function getAlertIcon(type: string) {
  switch (type) {
    case 'expiration_warning':
    case 'expiration_critical':
      return <Clock className="w-5 h-5" />
    case 'expired':
      return <AlertTriangle className="w-5 h-5" />
    case 'low_stock':
    case 'dead_stock':
      return <Package className="w-5 h-5" />
    default:
      return <Bell className="w-5 h-5" />
  }
}

function getSeverityVariant(severity: string): 'safe' | 'warning' | 'critical' | 'secondary' {
  switch (severity) {
    case 'critical':
      return 'critical'
    case 'warning':
      return 'warning'
    case 'info':
      return 'secondary'
    default:
      return 'secondary'
  }
}

export function AlertsPage() {
  const { t } = useTranslation()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [summary, setSummary] = useState({ total_unread: 0, critical: 0, warning: 0, info: 0 })
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'unread'>('unread')

  useEffect(() => {
    fetchAlerts()
    fetchSummary()
  }, [filter])

  async function fetchAlerts() {
    try {
      setLoading(true)
      const response = await alertsApi.list({
        unread_only: filter === 'unread',
      })
      setAlerts(response.items || [])
    } catch (error) {
      console.error('Failed to fetch alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  async function fetchSummary() {
    try {
      const response = await alertsApi.getSummary()
      setSummary(response)
    } catch (error) {
      console.error('Failed to fetch summary:', error)
    }
  }

  async function handleMarkRead(id: string) {
    try {
      await alertsApi.markRead(id)
      setAlerts(alerts.map(a => a.id === id ? { ...a, is_read: true } : a))
      setSummary(s => ({ ...s, total_unread: Math.max(0, s.total_unread - 1) }))
    } catch (error) {
      console.error('Failed to mark as read:', error)
    }
  }

  async function handleMarkAllRead() {
    try {
      await alertsApi.markAllRead()
      setAlerts(alerts.map(a => ({ ...a, is_read: true })))
      setSummary(s => ({ ...s, total_unread: 0 }))
    } catch (error) {
      console.error('Failed to mark all as read:', error)
    }
  }

  return (
    <div className="space-y-6">
      <Header title={t('alerts.title')} alertCount={summary.total_unread} />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-16">
        <Card className="border-l-4 border-l-muted-foreground">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">סה"כ לא נקראו</p>
                <p className="text-2xl font-bold">{summary.total_unread}</p>
              </div>
              <Bell className="w-8 h-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-status-critical">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('alerts.critical')}</p>
                <p className="text-2xl font-bold text-status-critical">{summary.critical}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-status-critical" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-status-warning">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('alerts.warning')}</p>
                <p className="text-2xl font-bold text-status-warning">{summary.warning}</p>
              </div>
              <Clock className="w-8 h-8 text-status-warning" />
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-primary">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('alerts.info')}</p>
                <p className="text-2xl font-bold text-primary">{summary.info}</p>
              </div>
              <Package className="w-8 h-8 text-primary" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Actions */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <Button
            variant={filter === 'unread' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('unread')}
          >
            לא נקראו
          </Button>
          <Button
            variant={filter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilter('all')}
          >
            הכל
          </Button>
        </div>
        <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
          <CheckCheck className="w-4 h-4 ml-2" />
          {t('alerts.markAllRead')}
        </Button>
      </div>

      {/* Alerts List */}
      <Card>
        <CardContent className="p-0">
          <ScrollArea className="h-[500px]">
            {loading ? (
              <div className="p-8 text-center text-muted-foreground">
                {t('common.loading')}
              </div>
            ) : alerts.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <Bell className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>{t('alerts.noAlerts')}</p>
              </div>
            ) : (
              <div className="divide-y">
                {alerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-4 transition-colors hover:bg-muted/50 ${
                      !alert.is_read ? 'bg-primary/5' : ''
                    }`}
                    onClick={() => !alert.is_read && handleMarkRead(alert.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`p-2 rounded-full ${
                        alert.severity === 'critical' ? 'bg-status-critical/10 text-status-critical' :
                        alert.severity === 'warning' ? 'bg-status-warning/10 text-status-warning' :
                        'bg-muted text-muted-foreground'
                      }`}>
                        {getAlertIcon(alert.alert_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium truncate">{alert.title}</h4>
                          <Badge variant={getSeverityVariant(alert.severity)}>
                            {t(`alerts.${alert.severity}`)}
                          </Badge>
                          {!alert.is_read && (
                            <span className="w-2 h-2 rounded-full bg-primary" />
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {alert.message}
                        </p>
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatDistanceToNow(new Date(alert.created_at), {
                            addSuffix: true,
                            locale: he,
                          })}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  )
}

