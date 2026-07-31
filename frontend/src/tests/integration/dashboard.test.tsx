import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { DashboardPage } from '@/pages/DashboardPage'
import * as api from '@/lib/api'

vi.mock('@/lib/api', () => ({
  // NotificationBell (rendered inside <Header>, which DashboardPage
  // renders) imports the default axios instance directly for its own
  // alert fetch - stub it too so that unrelated fetch doesn't error.
  default: {
    get: vi.fn().mockResolvedValue({ data: { items: [] } }),
  },
  dashboardApi: {
    getKpis: vi.fn(),
    getExpirationRisk: vi.fn(),
    getInventoryDistribution: vi.fn(),
    getInventoryValue: vi.fn(),
    getLowStock: vi.fn(),
    getMovementTrend: vi.fn(),
    getRecentActivity: vi.fn(),
  },
  systemSettingsApi: {
    get: vi.fn(),
  },
}))

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}))

const baseKpis = {
  inventory_value_by_currency: { ILS: 20000 },
  items_in_stock: 12,
  at_risk_value_by_currency: { ILS: 1000 },
  at_risk_percentage: 5,
  low_stock_items: 2,
  critical_low_stock: 1,
  unread_alerts: 3,
  recent_receipts: 40,
  recent_dispatches: 15,
}

const baseRisk = {
  risk_levels: {
    safe: { quantity: 10, value_by_currency: { ILS: 1000 }, batches: 1 },
    caution: { quantity: 0, value_by_currency: {}, batches: 0 },
    warning: { quantity: 0, value_by_currency: {}, batches: 0 },
    critical: { quantity: 0, value_by_currency: {}, batches: 0 },
    expired: { quantity: 0, value_by_currency: {}, batches: 0 },
  },
  total_value_by_currency: { ILS: 1000 },
  color_codes: {},
}

const baseFxRates = {
  usd_to_ils: 3.7,
  eur_to_ils: 4.0,
  try_to_ils: 0.11,
  min_shelf_life_days: 180,
  updated_at: new Date().toISOString(),
}

const baseTrend = {
  period_days: 7,
  start_date: '2026-07-17',
  end_date: '2026-07-24',
  series: [
    { date: '2026-07-23', receipts: 10, dispatches: 4, scraps: 0 },
    { date: '2026-07-24', receipts: 6, dispatches: 2, scraps: 1 },
  ],
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
    vi.mocked(api.dashboardApi.getKpis).mockResolvedValue(baseKpis as any)
    vi.mocked(api.dashboardApi.getExpirationRisk).mockResolvedValue(baseRisk as any)
    vi.mocked(api.dashboardApi.getInventoryDistribution).mockResolvedValue({ items: [] } as any)
    vi.mocked(api.dashboardApi.getInventoryValue).mockResolvedValue({
      totals_by_currency: { ILS: 20000 },
      total_quantity: 100,
      items_with_stock: 12,
    } as any)
    vi.mocked(api.dashboardApi.getLowStock).mockResolvedValue({ items: [], count: 0, critical_count: 0 } as any)
    vi.mocked(api.dashboardApi.getMovementTrend).mockResolvedValue(baseTrend as any)
    vi.mocked(api.systemSettingsApi.get).mockResolvedValue(baseFxRates as any)
  })

  it('renders KPI cards once data loads', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.inventoryValue')).toBeInTheDocument()
    })
    expect(api.dashboardApi.getKpis).toHaveBeenCalled()
  })

  it('renders the Activity Trend chart with the default 7-day range', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.activityTrend')).toBeInTheDocument()
    })
    expect(api.dashboardApi.getMovementTrend).toHaveBeenCalledWith(7)
  })

  it('shows the empty state for Low Stock when there are no items', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.noLowStockItems')).toBeInTheDocument()
    })
  })

  it('renders Low Stock items when present', async () => {
    vi.mocked(api.dashboardApi.getLowStock).mockResolvedValue({
      items: [
        {
          item_id: '1',
          sku: 'INK-001',
          name: 'Black Ink',
          current_quantity: 5,
          reorder_point: 20,
          min_stock: 10,
          shortage: 15,
          is_critical: true,
        },
      ],
      count: 1,
      critical_count: 1,
    } as any)

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('Black Ink')).toBeInTheDocument()
    })
  })

  it('renders the currency breakdown card', async () => {
    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.currencyBreakdown')).toBeInTheDocument()
    })
  })

  it('shows the no-data state for the trend chart when the series is empty', async () => {
    vi.mocked(api.dashboardApi.getMovementTrend).mockResolvedValue({
      period_days: 7,
      start_date: '2026-07-17',
      end_date: '2026-07-24',
      series: [],
    } as any)

    renderDashboard()

    await waitFor(() => {
      expect(screen.getByText('dashboard.activityTrend')).toBeInTheDocument()
    })
    expect(screen.getAllByText('common.noData').length).toBeGreaterThan(0)
  })
})
