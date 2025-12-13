import { useState, useEffect } from 'react'
import { WifiOff, Wifi, CloudOff, RefreshCw, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { isOnline, getPendingCount, syncPendingOperations } from '@/lib/offline'
import api from '@/lib/api'

interface OfflineIndicatorProps {
  className?: string
}

export function OfflineIndicator({ className }: OfflineIndicatorProps) {
  const [online, setOnline] = useState(isOnline())
  const [pendingCount, setPendingCount] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ success: number; failed: number } | null>(null)

  useEffect(() => {
    const handleOnline = () => setOnline(true)
    const handleOffline = () => setOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Check pending operations count
    const checkPending = async () => {
      const count = await getPendingCount()
      setPendingCount(count)
    }

    checkPending()
    const interval = setInterval(checkPending, 5000)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(interval)
    }
  }, [])

  const handleSync = async () => {
    if (syncing || !online) return

    setSyncing(true)
    setSyncResult(null)

    try {
      const result = await syncPendingOperations(async (endpoint, method, data) => {
        if (method === 'POST') {
          await api.post(endpoint, data)
        } else if (method === 'PUT') {
          await api.put(endpoint, data)
        } else if (method === 'DELETE') {
          await api.delete(endpoint)
        }
      })

      setSyncResult(result)
      const count = await getPendingCount()
      setPendingCount(count)

      // Clear result after 3 seconds
      setTimeout(() => setSyncResult(null), 3000)
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  // Auto-sync when coming back online
  useEffect(() => {
    if (online && pendingCount > 0) {
      handleSync()
    }
  }, [online])

  // Don't show if online and no pending operations
  if (online && pendingCount === 0 && !syncResult) {
    return null
  }

  return (
    <div
      className={cn(
        'fixed bottom-4 left-4 z-40 flex items-center gap-2 px-3 py-2 rounded-lg shadow-lg transition-all duration-300',
        online
          ? pendingCount > 0
            ? 'bg-amber-500 text-white'
            : 'bg-green-500 text-white'
          : 'bg-red-500 text-white',
        className
      )}
    >
      {!online ? (
        <>
          <WifiOff className="w-4 h-4" />
          <span className="text-sm font-medium">אופליין</span>
          {pendingCount > 0 && (
            <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">
              {pendingCount} בהמתנה
            </span>
          )}
        </>
      ) : syncResult ? (
        <>
          <Check className="w-4 h-4" />
          <span className="text-sm font-medium">
            סונכרנו {syncResult.success} פעולות
          </span>
        </>
      ) : pendingCount > 0 ? (
        <>
          <CloudOff className="w-4 h-4" />
          <span className="text-sm font-medium">{pendingCount} פעולות בהמתנה</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleSync}
            disabled={syncing}
            className="h-6 px-2 text-white hover:bg-white/20"
          >
            <RefreshCw className={cn('w-3 h-3', syncing && 'animate-spin')} />
          </Button>
        </>
      ) : (
        <>
          <Wifi className="w-4 h-4" />
          <span className="text-sm font-medium">מחובר</span>
        </>
      )}
    </div>
  )
}
