import { useState, useEffect, useCallback } from 'react'

interface NetworkStatus {
  isOnline: boolean
  effectiveType?: 'slow-2g' | '2g' | '3g' | '4g'
  downlink?: number
  rtt?: number
  saveData?: boolean
}

export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>(() => ({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
  }))

  const updateNetworkInfo = useCallback(() => {
    const connection = (navigator as any).connection

    setStatus({
      isOnline: navigator.onLine,
      effectiveType: connection?.effectiveType,
      downlink: connection?.downlink,
      rtt: connection?.rtt,
      saveData: connection?.saveData,
    })
  }, [])

  useEffect(() => {
    // Initial update
    updateNetworkInfo()

    // Listen for online/offline events
    window.addEventListener('online', updateNetworkInfo)
    window.addEventListener('offline', updateNetworkInfo)

    // Listen for connection changes (if supported)
    const connection = (navigator as any).connection
    if (connection) {
      connection.addEventListener('change', updateNetworkInfo)
    }

    return () => {
      window.removeEventListener('online', updateNetworkInfo)
      window.removeEventListener('offline', updateNetworkInfo)
      if (connection) {
        connection.removeEventListener('change', updateNetworkInfo)
      }
    }
  }, [updateNetworkInfo])

  return status
}

// Helper hook for data-saver mode
export function useDataSaver(): boolean {
  const { saveData, effectiveType } = useNetworkStatus()
  return saveData || effectiveType === 'slow-2g' || effectiveType === '2g'
}

