import { useCallback, useEffect, useState } from 'react'
import {
  dashboardApi,
  systemSettingsApi,
  type DashboardKPIs,
  type SystemSettings,
  type InventoryValue,
  type LowStockResponse,
  type MovementTrend,
} from '@/lib/api'

export type TrendRangeDays = 7 | 30 | 90

interface DashboardData {
  kpis: DashboardKPIs | null
  riskData: any
  distribution: any[]
  fxRates: SystemSettings | null
  inventoryValue: InventoryValue | null
  lowStock: LowStockResponse | null
  movementTrend: MovementTrend | null
  trendDays: TrendRangeDays
  setTrendDays: (days: TrendRangeDays) => void
  loading: boolean
  trendLoading: boolean
}

export function useDashboardData(): DashboardData {
  const [kpis, setKpis] = useState<DashboardKPIs | null>(null)
  const [riskData, setRiskData] = useState<any>(null)
  const [distribution, setDistribution] = useState<any[]>([])
  const [fxRates, setFxRates] = useState<SystemSettings | null>(null)
  const [inventoryValue, setInventoryValue] = useState<InventoryValue | null>(null)
  const [lowStock, setLowStock] = useState<LowStockResponse | null>(null)
  const [movementTrend, setMovementTrend] = useState<MovementTrend | null>(null)
  const [trendDays, setTrendDays] = useState<TrendRangeDays>(7)
  const [loading, setLoading] = useState(true)
  const [trendLoading, setTrendLoading] = useState(false)

  useEffect(() => {
    async function fetchData() {
      try {
        const [kpisRes, riskRes, distRes, fxRes, inventoryValueRes, lowStockRes, trendRes] = await Promise.all([
          dashboardApi.getKpis(),
          dashboardApi.getExpirationRisk(),
          dashboardApi.getInventoryDistribution(),
          systemSettingsApi.get(),
          dashboardApi.getInventoryValue(),
          dashboardApi.getLowStock(),
          dashboardApi.getMovementTrend(7),
        ])
        setKpis(kpisRes)
        setRiskData(riskRes)
        setDistribution(distRes.items || [])
        setFxRates(fxRes)
        setInventoryValue(inventoryValueRes)
        setLowStock(lowStockRes)
        setMovementTrend(trendRes)
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
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
    riskData,
    distribution,
    fxRates,
    inventoryValue,
    lowStock,
    movementTrend,
    trendDays,
    setTrendDays: handleSetTrendDays,
    loading,
    trendLoading,
  }
}
