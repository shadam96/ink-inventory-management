import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import i18n from '@/i18n'
import {
  dashboardApi,
  systemSettingsApi,
  type AttentionItems,
  type DashboardKPIs,
  type ExpiryTimeline,
  type MovementTrend,
  type StockCoverage,
  type SystemSettings,
} from '@/lib/api'

export type TrendRangeDays = 7 | 30 | 90

interface DashboardData {
  kpis: DashboardKPIs | null
  fxRates: SystemSettings | null
  expiryTimeline: ExpiryTimeline | null
  stockCoverage: StockCoverage | null
  attention: AttentionItems | null
  movementTrend: MovementTrend | null
  trendDays: TrendRangeDays
  setTrendDays: (days: TrendRangeDays) => void
  loading: boolean
  trendLoading: boolean
}

export function useDashboardData(): DashboardData {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null)
  const [fxRates, setFxRates] = useState<SystemSettings | null>(null)
  const [expiryTimeline, setExpiryTimeline] = useState<ExpiryTimeline | null>(null)
  const [stockCoverage, setStockCoverage] = useState<StockCoverage | null>(null)
  const [attention, setAttention] = useState<AttentionItems | null>(null)
  const [movementTrend, setMovementTrend] = useState<MovementTrend | null>(null)
  const [trendDays, setTrendDays] = useState<TrendRangeDays>(90)
  const [loading, setLoading] = useState(true)
  const [trendLoading, setTrendLoading] = useState(false)

  useEffect(() => {
    async function fetchData() {
      // Settled one by one, so a failing endpoint only empties its own card.
      const results = await Promise.allSettled([
        dashboardApi.getKpis().then(setKpis),
        systemSettingsApi.get().then(setFxRates),
        dashboardApi.getExpiryTimeline().then(setExpiryTimeline),
        dashboardApi.getStockCoverage().then(setStockCoverage),
        dashboardApi.getAttention().then(setAttention),
        dashboardApi.getMovementTrend(90).then(setMovementTrend),
      ])
      const failures = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      if (failures.length > 0) {
        console.error('Failed to fetch dashboard data:', failures.map((failure) => failure.reason))
        toast.error(i18n.t('dashboard.loadError'))
      }
      setLoading(false)
    }
    fetchData()
  }, [])

  // Range-selector changes only refetch the trend series, not the whole page.
  useEffect(() => {
    if (loading) return
    let cancelled = false
    async function fetchTrend() {
      setTrendLoading(true)
      try {
        const trendRes = await dashboardApi.getMovementTrend(trendDays)
        if (!cancelled) setMovementTrend(trendRes)
      } catch (error) {
        console.error('Failed to fetch movement trend:', error)
      } finally {
        if (!cancelled) setTrendLoading(false)
      }
    }
    fetchTrend()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trendDays])

  const handleSetTrendDays = useCallback((days: TrendRangeDays) => setTrendDays(days), [])

  return {
    kpis,
    fxRates,
    expiryTimeline,
    stockCoverage,
    attention,
    movementTrend,
    trendDays,
    setTrendDays: handleSetTrendDays,
    loading,
    trendLoading,
  }
}
