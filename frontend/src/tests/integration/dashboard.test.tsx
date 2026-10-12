import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { DashboardPage } from '@/pages/DashboardPage'
import * as api from '@/lib/api'
import type {
  AttentionItems,
  DashboardKPIs,
  ExpiryBucket,
  ExpiryBucketKey,
  ExpiryTimeline,
  MovementTrend,
  MovementTrendPoint,
  StockCoverage,
  SystemSettings,
} from '@/lib/api'

vi.mock('@/lib/api', () => ({
  // NotificationBell (rendered inside <Header>, which DashboardPage
  // renders) imports the default axios instance directly for its own
  // alert fetch - stub it too so that unrelated fetch doesn't error.
  default: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
  },
  dashboardApi: {
    getKpis: vi.fn(),
    getMovementTrend: vi.fn(),
    getExpiryTimeline: vi.fn(),
    getStockCoverage: vi.fn(),
    getAttention: vi.fn(),
  },
  systemSettingsApi: {
    get: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', dir: () => 'ltr' },
  }),
}))

const baseKpis: DashboardKPIs = {
  inventory_value_by_currency: { ILS: 20000 },
  inventory_value_30d_ago_by_currency: { ILS: 18000 },
  items_in_stock: 12,
  at_risk_value_by_currency: { ILS: 1000 },
  at_risk_percentage: 5,
  low_stock_items: 2,
  critical_low_stock: 1,
  unread_alerts: 3,
  recent_receipts: 40,
  recent_dispatches: 15,
  write_off_90d_value_by_currency: { ILS: 300 },
  write_off_90d_rate: 1.5,
  turnover_annualized: 4.2,
  days_on_hand: 87,
}

const bucket = (key: ExpiryBucketKey, ils: number): ExpiryBucket => ({
  key,
  value_by_currency: ils ? { ILS: ils } : {},
  quantity_by_unit: ils ? { L: ils / 10 } : {},
  batches: ils ? 1 : 0,
})

const baseTimeline: ExpiryTimeline = {
  buckets: [
    bucket('expired', 0),
    bucket('d0_30', 1000),
    bucket('d31_60', 0),
    bucket('d61_90', 0),
    bucket('d91_180', 5000),
    bucket('d181_plus', 14000),
  ],
}

const emptyAttention: AttentionItems = { expired_on_shelf: [], expiring_soon: [], below_min: [], dead_stock: [] }

const baseCoverage: StockCoverage = {
  window_days: 90,
  items: [
    {
      item_id: '1', sku: 'UV-C', name: 'UV Cyan', color: 'cyan', unit: 'L', quantity: 16,
      reorder_point: 20, min_stock: 5, avg_daily_usage: 0.6, days_of_supply: 26.7, status: 'below_reorder',
    },
    {
      item_id: '2', sku: 'FLX-W', name: 'Flexo White', color: 'white', unit: 'KG', quantity: 40,
      reorder_point: 10, min_stock: 4, avg_daily_usage: 0, days_of_supply: null, status: 'ok',
    },
  ],
}

const baseFxRates: SystemSettings = {
  usd_to_ils: 3.7,
  eur_to_ils: 4.0,
  try_to_ils: 0.11,
  min_shelf_life_days: 180,
  updated_at: new Date().toISOString(),
}

const trendPoint = (date: string, receipts: number, outbound: number): MovementTrendPoint => ({
  date,
  receipts,
  dispatches: outbound,
  consumptions: 0,
  scraps: 0,
  receipts_value_by_currency: { ILS: receipts * 10 },
  outbound_value_by_currency: { ILS: outbound * 10 },
})

const baseTrend: MovementTrend = {
  period_days: 7,
  start_date: '2026-07-17',
  end_date: '2026-07-24',
  series: [trendPoint('2026-07-23', 10, 4), trendPoint('2026-07-24', 6, 2)],
}

function renderDashboard() {
  return render(
    <BrowserRouter>
      <DashboardPage />
    </BrowserRouter>
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.dashboardApi.getKpis).mockResolvedValue(baseKpis)
    vi.mocked(api.dashboardApi.getExpiryTimeline).mockResolvedValue(baseTimeline)
    vi.mocked(api.dashboardApi.getStockCoverage).mockResolvedValue(baseCoverage)
    vi.mocked(api.dashboardApi.getAttention).mockResolvedValue(emptyAttention)
    vi.mocked(api.dashboardApi.getMovementTrend).mockResolvedValue(baseTrend)
    vi.mocked(api.systemSettingsApi.get).mockResolvedValue(baseFxRates)
  })

  it('renders the four KPI cards once data loads', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.inventoryValue')).toBeInTheDocument()
    })
    expect(screen.getByText('dashboard.expiring30')).toBeInTheDocument()
    expect(screen.getByText('dashboard.belowReorder')).toBeInTheDocument()
    expect(screen.getByText('dashboard.turnover')).toBeInTheDocument()
    expect(screen.getByText('dashboard.vs30dAgo')).toBeInTheDocument()
  })

  it('no longer shows the removed widgets', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.inventoryValue')).toBeInTheDocument()
    })
    expect(screen.queryByText('dashboard.unreadAlerts')).not.toBeInTheDocument()
    expect(screen.queryByText('dashboard.currencyBreakdown')).not.toBeInTheDocument()
    expect(screen.queryByText('dashboard.inventoryDistribution')).not.toBeInTheDocument()
    expect(screen.queryByText('dashboard.expirationRisk')).not.toBeInTheDocument()
  })

  it('loads the activity trend with the default 90-day range', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.activityTrend')).toBeInTheDocument()
    })
    expect(api.dashboardApi.getMovementTrend).toHaveBeenCalledWith(90)
  })

  it('shows the all-clear state when nothing needs attention', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.nothingNeedsAttention')).toBeInTheDocument()
    })
  })

  it('lists lots and items that need attention', async () => {
    vi.mocked(api.dashboardApi.getAttention).mockResolvedValue({
      ...emptyAttention,
      expiring_soon: [
        {
          batch_id: 'b1', batch_number: 'UV-K-L2601', item_id: '3', sku: 'UV-K', name: 'UV Black',
          unit: 'L', quantity: 12, value: 456, currency: 'USD', expiration_date: '2026-08-01',
          days_until_expiration: 9, location_code: 'A-01',
        },
      ],
      below_min: [
        { item_id: '4', sku: 'SOL-Y', name: 'Solvent Yellow', unit: 'L', quantity: 2, min_stock: 10, reorder_point: 25 },
      ],
    })

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('UV Black')).toBeInTheDocument()
    })
    expect(screen.getByText('Solvent Yellow')).toBeInTheDocument()
    expect(screen.getByText('UV-K-L2601 · A-01')).toBeInTheDocument()
  })

  it('shows days of supply and lists items with no demand separately', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.stockCoverage')).toBeInTheDocument()
    })
    expect(screen.getByText('UV Cyan')).toBeInTheDocument()
    expect(screen.getByText('dashboard.statusBelowReorder')).toBeInTheDocument()
    expect(screen.getByText('dashboard.noDemand')).toBeInTheDocument()
    expect(screen.getByText('Flexo White')).toBeInTheDocument()
  })

  it('shows the 90-day write-off under the expiry timeline', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.expiryTimeline')).toBeInTheDocument()
    })
    expect(screen.getByText('dashboard.writeOff90d')).toBeInTheDocument()
  })

  it('shows the no-data state for the trend chart when the series is empty', async () => {
    vi.mocked(api.dashboardApi.getMovementTrend).mockResolvedValue({
      period_days: 7,
      start_date: '2026-07-17',
      end_date: '2026-07-24',
      series: [],
    })

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.activityTrend')).toBeInTheDocument()
    })
    expect(screen.getAllByText('common.noData').length).toBeGreaterThan(0)
  })
})
